/**
 * IndexedDB-backed persistence for in-progress drafts.
 *
 * This layer is intentionally framework-agnostic: it knows nothing about Vue or
 * Frappe. It stores one {@link DraftRecord} per draft, keyed by the draft's name, and
 * notifies other tabs of the same origin when a record changes so they can stay coherent.
 * The reactive orchestration (debounced server sync, lazy row creation, reconciliation)
 * lives in `useDraftSync`.
 */
import { get, update, del, entries, clear, createStore, promisifyRequest } from 'idb-keyval'
import { isEditorContentEmpty } from '@/utils'

export type DraftType = 'Discussion' | 'Comment'
export type DraftMode = 'New' | 'Edit'

/** What a draft relates to. Singleton drafts (comments, edits) are uniquely
 *  identified by this; standalone new-discussion drafts carry no reference. */
export interface DraftIdentity {
  type: DraftType
  mode: DraftMode
  referenceDoctype?: string | null
  referenceName?: string | null
}

/** The editable content a draft holds. `title`/`project` only apply to discussions. */
export interface DraftPayload {
  title?: string
  content: string
  project?: string | null
}

export interface DraftRecord {
  /** The draft's name, given when it is started: its key here, the `?draft=` in its URL and
   *  its GP Draft name on the server. It never changes, and no two drafts share it. */
  key: string
  identity: DraftIdentity
  payload: DraftPayload
  /** Equal to `key` once the server row exists, else null. */
  serverName: string | null
  /** The session user who authored this draft. The IndexedDB store is origin-wide, so this
   *  guards a shared browser profile: recovery only adopts the current user's own orphans,
   *  never uploading a logged-out user's draft under the next account. Absent on records
   *  written before this field existed — treated as "not mine" and skipped. */
  user?: string | null
  /** Last local edit, epoch ms. Drives reconciliation against the server. */
  updatedAt: number
  /** Last successful server push, epoch ms, or null if never synced. */
  syncedAt: number | null
}

/** Title or non-empty body: the threshold for saving a draft at all. */
export function hasContent(payload: DraftPayload): boolean {
  return !isEditorContentEmpty(payload.content) || (payload.title ?? '').trim().length > 0
}

/** A new draft name: 20 random lowercase letters and digits, the form GP Draft accepts. */
export function newDraftName(): string {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
  const bytes = crypto.getRandomValues(new Uint8Array(20))
  return Array.from(bytes, (byte) => alphabet[byte % alphabet.length]).join('')
}

const store = createStore('gameplan-drafts', 'records')

let converted: Promise<void> | null = null
/** Every read and write waits until records from older versions are converted, once. */
function ready() {
  converted ??= convertOldRecords()
  return converted
}

export async function getDraftRecord(key: string): Promise<DraftRecord | undefined> {
  await ready()
  return get<DraftRecord>(key, store)
}

/**
 * Writes a record. One whose server row exists stays saved until it is deleted: a writer
 * that has not heard of the save yet (another tab, the recovery sweep) must not undo it, or
 * a later delete would skip the row. `update` reads and writes in one transaction.
 */
export async function putDraftRecord(record: DraftRecord): Promise<void> {
  await ready()
  return update<DraftRecord>(
    record.key,
    (stored) => ({ ...record, serverName: record.serverName ?? stored?.serverName ?? null }),
    store,
  )
}

export async function deleteDraftRecord(key: string): Promise<void> {
  await ready()
  return del(key, store)
}

export async function listDraftRecords(): Promise<DraftRecord[]> {
  await ready()
  return entries<string, DraftRecord>(store).then((all) => all.map(([, record]) => record))
}

/**
 * Runs `task` while holding the lock `name`: across tabs with Web Locks, or where those are
 * missing, queued behind the other tasks of this tab.
 */
const queues = new Map<string, Promise<unknown>>()
export function withLock<T>(name: string, task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request(name, task) as Promise<T>
  }
  const run = (queues.get(name) ?? Promise.resolve()).then(task, task)
  queues.set(
    name,
    run.catch(() => {}),
  )
  return run
}

/**
 * Runs `task` as the only writer of draft `name` in this browser, so saving and deleting it
 * never interleave and the server sees its writes in order.
 */
export function withDraftLock<T>(name: string, task: () => Promise<T>): Promise<T> {
  return withLock(`gp-draft:${name}`, task)
}

/**
 * Older versions keyed a reply or edit draft by its target (`Comment::New::GP Discussion::42`)
 * and a new discussion by its server name or a per-tab id (`Discussion::New::…`). Each such
 * record moves to its draft's name: the server name if it has a row, else a new name. One
 * transaction, so a crash leaves all or nothing.
 */
function convertOldRecords(): Promise<void> {
  return store('readwrite', async (records) => {
    const keys = await promisifyRequest(records.getAllKeys())
    const values = await promisifyRequest(records.getAll())
    keys.forEach((oldKey, i) => {
      if (!String(oldKey).includes('::')) return
      const old = values[i] as Partial<DraftRecord> & { deleted?: boolean }
      // Queued deletions carry no identity, and tombstones are drafts already deleted.
      if (old.identity && !old.deleted) {
        const key = old.serverName || newDraftName()
        records.put({ ...old, key, serverName: old.serverName ?? null }, key)
      }
      records.delete(oldKey)
    })
    return promisifyRequest(records.transaction)
  })
}

/** Wipes every local draft. Only on a user switch: after logout the same person may return. */
export function clearDraftStore(): Promise<void> {
  return clear(store)
}

/** The target a singleton draft is for, as a string: equal for every draft of one target. */
export function singletonKey(identity: DraftIdentity): string {
  const { type, mode, referenceDoctype, referenceName } = identity
  return [type, mode, referenceDoctype ?? '', referenceName ?? ''].join('::')
}

type DraftChangeListener = (key: string) => void

const CHANNEL_NAME = 'gameplan-drafts'
let channel: BroadcastChannel | null | undefined

function getChannel(): BroadcastChannel | null {
  if (channel === undefined) {
    channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL_NAME) : null
  }
  return channel
}

/** Tell other tabs a record changed (or was deleted) so they can reload it. */
export function broadcastDraftChange(key: string): void {
  getChannel()?.postMessage({ key })
}

/** Subscribe to cross-tab draft changes. Returns an unsubscribe function. */
export function onDraftChange(listener: DraftChangeListener): () => void {
  const ch = getChannel()
  if (!ch) return () => {}
  const handler = (event: MessageEvent) => {
    const key = (event.data as { key?: string } | null)?.key
    if (key) listener(key)
  }
  ch.addEventListener('message', handler)
  return () => ch.removeEventListener('message', handler)
}
