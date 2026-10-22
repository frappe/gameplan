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
import { withLock } from '@/utils/locks'

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
  /** The draft's name for life: its key here, its `?draft=` and its GP Draft name. */
  key: string
  identity: DraftIdentity
  payload: DraftPayload
  /** Whether the server row exists under `key`. */
  saved: boolean
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
  converted ??= convertOldRecords().catch((error) => {
    converted = null
    throw error
  })
  return converted
}

export async function getDraftRecord(key: string): Promise<DraftRecord | undefined> {
  await ready()
  return get<DraftRecord>(key, store)
}

/** A saved record stays saved until deleted, so a writer that missed the save cannot undo it
 *  and make a later delete skip the row. */
export async function putDraftRecord(record: DraftRecord): Promise<void> {
  await ready()
  return update<DraftRecord>(
    record.key,
    (stored) => ({ ...record, saved: record.saved || stored?.saved || false }),
    store,
  )
}

export async function deleteDraftRecord(key: string): Promise<void> {
  await ready()
  return del(key, store)
}

/** Move the latest unsynced copy atomically, including edits made during server lookup. */
export async function moveDraftRecord(
  key: string,
  replacementKey: string,
): Promise<DraftRecord | null> {
  await ready()
  return store('readwrite', async (records) => {
    const current = (await promisifyRequest(records.get(key))) as DraftRecord | undefined
    if (!current || current.updatedAt <= (current.syncedAt ?? 0)) return null
    const replacement = { ...current, key: replacementKey, saved: false }
    records.put(replacement, replacementKey)
    records.delete(key)
    await promisifyRequest(records.transaction)
    return replacement
  })
}

export async function listDraftRecords(): Promise<DraftRecord[]> {
  await ready()
  return entries<string, DraftRecord>(store).then((all) => all.map(([, record]) => record))
}

/** Saves and deletes of one draft never interleave, so the server sees them in order. */
export function withDraftLock<T>(name: string, task: () => Promise<T>): Promise<T> {
  return withLock(`gp-draft:${name}`, task)
}

/** Converts legacy singleton keys and serverName fields in one transaction. */
function convertOldRecords(): Promise<void> {
  return store('readwrite', async (records) => {
    const keys = await promisifyRequest(records.getAllKeys())
    const values = await promisifyRequest(records.getAll())
    keys.forEach((oldKey, i) => {
      const value = values[i]
      if (!value || typeof value !== 'object') {
        records.delete(oldKey)
        return
      }
      const { serverName, ...old } = value
      const legacy = String(oldKey).includes('::')
      if (legacy && (!old.identity || old.deleted)) records.delete(oldKey)
      else if (legacy || typeof old.saved !== 'boolean') {
        const key = legacy ? serverName || newDraftName() : String(oldKey)
        records.put({ ...old, key, saved: old.saved ?? Boolean(serverName) }, key)
        if (legacy) records.delete(oldKey)
      }
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

type DraftChangeListener = (key: string, replacementKey?: string) => void

const CHANNEL_NAME = 'gameplan-drafts'
let channel: BroadcastChannel | null | undefined

function getChannel(): BroadcastChannel | null {
  if (channel === undefined) {
    channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL_NAME) : null
  }
  return channel
}

/** Tell other tabs a record changed (or was deleted) so they can reload it. */
export function broadcastDraftChange(key: string, replacementKey?: string): void {
  getChannel()?.postMessage({ key, replacementKey })
}

/** Subscribe to cross-tab draft changes. Returns an unsubscribe function. */
export function onDraftChange(listener: DraftChangeListener): () => void {
  const ch = getChannel()
  if (!ch) return () => {}
  const handler = (event: MessageEvent) => {
    const change = event.data as { key?: string; replacementKey?: string } | null
    if (change?.key) listener(change.key, change.replacementKey)
  }
  ch.addEventListener('message', handler)
  return () => ch.removeEventListener('message', handler)
}
