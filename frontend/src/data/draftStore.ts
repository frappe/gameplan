/**
 * IndexedDB-backed persistence for in-progress drafts.
 *
 * This layer is intentionally framework-agnostic: it knows nothing about Vue or
 * Frappe. It stores one {@link DraftRecord} per logical draft, keyed by a stable
 * string, and notifies other tabs of the same origin when a record changes so they
 * can stay coherent. The reactive orchestration (debounced server sync, lazy row
 * creation, reconciliation) lives in `useDraftSync`.
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
  /** Stable local key. Singletons derive it from identity; standalone drafts use
   *  their server name once created, a per-instance token before that. */
  key: string
  identity: DraftIdentity
  payload: DraftPayload
  /** GP Draft.name once the row exists on the server, else null. */
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

const store = createStore('gameplan-drafts', 'records')

export function getDraftRecord(key: string): Promise<DraftRecord | undefined> {
  return get<DraftRecord>(key, store)
}

export function putDraftRecord(record: DraftRecord): Promise<void> {
  return set(record.key, record, store)
}

export function deleteDraftRecord(key: string): Promise<void> {
  return del(key, store)
}

export function listDraftRecords(): Promise<DraftRecord[]> {
  return entries<string, DraftRecord>(store).then((all) => all.map(([, record]) => record))
}

/**
 * Wipe every locally stored draft, regardless of owner. `record.user` already keeps
 * another account's drafts from being read back into an editor on a shared browser
 * (see useDraftSync's `load()`), so this is only called when a *different* user is
 * detected on this device (offline.ts's guardAgainstUserSwitch) - not on a plain
 * logout, where the same person may log back in and expect their draft still there.
 */
export function clearDraftStore(): Promise<void> {
  return clear(store)
}

/** Deterministic key for singleton drafts — the same target always resolves to one
 *  record, so two tabs editing the same post share it instead of forking. */
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
