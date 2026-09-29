/**
 * IndexedDB-backed persistence for in-progress drafts.
 *
 * This layer is intentionally framework-agnostic: it knows nothing about Vue or
 * Frappe. It stores one {@link DraftRecord} per draft, keyed by the draft's name, and
 * notifies other tabs of the same origin when a record changes so they can stay coherent.
 * The reactive orchestration (debounced server sync, lazy row creation, reconciliation)
 * lives in `useDraftSync`.
 */
import { get, set, del, entries, clear, createStore } from 'idb-keyval'

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

export async function putDraftRecord(record: DraftRecord): Promise<void> {
  await ready()
  return set(record.key, record, store)
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
 * Runs `task` as the only writer of draft `name` in this browser, across tabs, so saving and
 * deleting it never interleave and the server sees its writes in order.
 */
const queues = new Map<string, Promise<unknown>>()
export function withDraftLock<T>(name: string, task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request(`gp-draft:${name}`, task) as Promise<T>
  }
  const run = (queues.get(name) ?? Promise.resolve()).then(task, task)
  queues.set(
    name,
    run.catch(() => {}),
  )
  return run
}

/**
 * Older versions keyed a reply or edit draft by its target (`Comment::New::GP Discussion::42`)
 * and a new discussion by its server name or a per-tab id (`Discussion::New::…`). Each such
 * record moves to its draft's name: the server name if it has a row, else a new name. One
 * transaction, so a crash leaves all or nothing.
 */
function convertOldRecords(): Promise<void> {
  return store('readwrite', (records) => {
    return new Promise((resolve, reject) => {
      const cursor = records.openCursor()
      cursor.onerror = () => reject(cursor.error)
      cursor.onsuccess = () => {
        const entry = cursor.result
        if (!entry) {
          records.transaction.oncomplete = () => resolve()
          records.transaction.onerror = () => reject(records.transaction.error)
          return
        }
        const old = entry.value as Partial<DraftRecord>
        if (String(entry.key).includes('::')) {
          if (old.identity) {
            const key = old.serverName || newDraftName()
            records.put({ ...old, key, serverName: old.serverName ?? null }, key)
          }
          entry.delete()
        }
        entry.continue()
      }
    })
  })
}

/** Wipes every local draft. Only on a user switch: after logout the same person may return. */
export function clearDraftStore(): Promise<void> {
  return clear(store)
}

/** Whether a record is a draft for this target (a reply or edit), matched by identity. */
export function isDraftFor(record: DraftRecord, identity: DraftIdentity): boolean {
  const id = record.identity
  return (
    id.type === identity.type &&
    id.mode === identity.mode &&
    (id.referenceDoctype ?? null) === (identity.referenceDoctype ?? null) &&
    (id.referenceName ?? null) === (identity.referenceName ?? null)
  )
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
