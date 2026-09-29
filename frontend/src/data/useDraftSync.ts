/**
 * useDraftSync — keep an in-progress draft synced across reloads, tabs, and devices.
 *
 * Backed by {@link module:data/draftStore} (IndexedDB, instant + durable) in front of a
 * `GP Draft` row on the server (authoritative + cross-device). Every edit is written to
 * IndexedDB immediately and pushed to the server on a debounce. The server row is created
 * lazily on the first saveable change, so we never persist empty drafts.
 *
 * Every draft has one name from its first keystroke (see draftStore): its local key, its
 * `?draft=` URL and its GP Draft row. Saving creates the row under that name, or updates it
 * if it exists, so a retry never makes a second row. The server refuses a deleted name, so
 * nothing can bring a deleted draft back; whoever holds a copy drops it when told.
 *
 * Two kinds of drafts (see {@link DraftIdentity}):
 *  - Singleton (comment-in-progress, in-flight edit): one draft per (user, type, mode,
 *    target), found by its target. Two tabs editing the same thing share it.
 *  - Standalone (new discussion): each composition is its own draft.
 */
import {
  ref,
  computed,
  watch,
  toRaw,
  toValue,
  nextTick,
  onScopeDispose,
  type MaybeRefOrGetter,
} from 'vue'
import { call, debounce, toast, useDoctype } from 'frappe-ui'
import { isNetworkError, refuseOffline } from '@/data/offline/requests'
import { isOnline, onReconnect } from './online'
import { session } from './session'
import { createDraft, drafts } from './drafts'
import { captureError } from '@/utils/errorReporting'
import { errorType } from '@/utils/errorMessage'
import {
  getDraftRecord,
  hasContent,
  putDraftRecord,
  deleteDraftRecord,
  listDraftRecords,
  newDraftName,
  withDraftLock,
  withLock,
  isDraftFor,
  broadcastDraftChange,
  onDraftChange,
  type DraftIdentity,
  type DraftPayload,
  type DraftRecord,
} from './draftStore'

export type { DraftIdentity, DraftPayload } from './draftStore'

const FIND_DRAFT = 'gameplan.gameplan.doctype.gp_draft.gp_draft.find_my_draft'
const COMMIT_DRAFT = 'gameplan.gameplan.doctype.gp_draft.gp_draft.commit_draft'

/**
 * How long a composer waits for its stored copies before it opens blank.
 *
 * A lookup that REJECTS is caught and falls back. A lookup that never settles is not:
 * `fetch` has no timeout of its own, and an IndexedDB request blocked by another tab's
 * version change fires neither handler. `data` would stay null forever, and a composer
 * gated on it would sit inert with no way to write or post a comment at all.
 */
const RESOLVE_TIMEOUT_MS = 8000

/** Resolves to null after `ms`. Raced against a lookup to bound how long it can hang. */
function timeout(ms: number): Promise<null> {
  return new Promise((resolve) => setTimeout(() => resolve(null), ms))
}

export interface UseDraftSyncOptions {
  /** What this draft is for. May be reactive. */
  identity: MaybeRefOrGetter<DraftIdentity>
  /** For standalone drafts, the draft's name bound to the URL (`?draft=`). Read on load to
   *  resume a draft; for a new one, `onCreate` hands the name out to put there. */
  draftName?: MaybeRefOrGetter<string | null>
  /** When false, the composable is dormant: no load, no persistence. Flipping it true (e.g.
   *  when an inline editor opens) triggers the initial load + restore. Defaults to true. */
  enabled?: MaybeRefOrGetter<boolean>
  /** Debounce for the server push. IndexedDB writes are always immediate. Defaults to 500ms. */
  debounceMs?: number
  /** Gate persistence on meaningful content. Defaults to "title or body is non-empty". */
  canSave?: (payload: DraftPayload) => boolean
  /** Seed `data` when no stored draft is found (e.g. the live document for an edit). */
  initialPayload?: () => DraftPayload
  /** Called once when a new draft is first saved here, with its name — lets standalone
   *  callers put it in the URL, so a reload (even offline) resumes it. */
  onCreate?: (name: string) => void
}

/** The `GP Draft` fields this module reads off a fetched row. */
interface ServerDraftDoc {
  name: string
  owner?: string
  content?: string
  title?: string
  project?: string | null
}

/** Where a draft starts from once its stored copies have been looked up and compared. */
export interface ResolvedDraft {
  /** The draft's name: the local record's, the server row's, or a new draft's. */
  name: string
  payload: DraftPayload
  /** Whether a `GP Draft` row by this name exists. A draft only ever has its own name, so
   *  there is no second name here to disagree with it. */
  saved: boolean
  /** Who the draft belongs to, or null while unknown. Unknown, or anyone but the session
   *  user, makes it read-only. */
  owner: string | null
  updatedAt: number
  syncedAt: number | null
  /** A stored draft with content was found, rather than a blank start. */
  restored: boolean
  /** The winning copy is not in IndexedDB yet and has to be written there. */
  needsLocalWrite: boolean
}

/**
 * Decide where a composer starts: the local copy, the server row, or a blank seed.
 *
 * Pure, so the precedence rules are readable and checkable on their own. The rules:
 *
 *  - A local record that belongs to someone else does not exist. The IndexedDB store is
 *    origin-wide, so on a shared browser profile a draft for this target may have been
 *    written by a previously logged-in user. Restoring it would surface their
 *    draft and sync our edits onto their server row. Records written before the `user`
 *    field existed are indistinguishable from another account's, so they go too. One that
 *    reached the server still comes back through `server`.
 *  - Un-pushed local edits beat the server copy: they are newer by definition.
 *  - A draft is readable by anyone holding its name (a shared `?draft=` URL), but only its
 *    owner can write it. A foreign server draft wins over everything else and opens
 *    read-only: the reader never gets a buffer of their own to save.
 *  - A named draft that neither copy vouches for has an unknown owner, so it stays
 *    read-only. Assuming the reader owns it would let them type into someone else's row.
 */
export function reconcileDraft(input: {
  local: DraftRecord | null
  server: ServerDraftDoc | null
  seed: DraftPayload
  /** Null while the session is still resolving; every stored copy is then foreign. */
  sessionUser: string | null
  /** The name the draft was opened by, or null for a new composition. */
  opened: string | null
  /** The name a new composition gets when neither copy is taken. */
  name: string
}): ResolvedDraft {
  const { server, seed, sessionUser } = input
  const local = input.local?.user === sessionUser ? input.local : null
  const base = {
    owner: sessionUser,
    restored: false,
    needsLocalWrite: false,
  }

  if (server?.owner && server.owner !== sessionUser) {
    const payload = payloadFromDoc(server, seed)
    return {
      ...base,
      name: server.name,
      payload,
      saved: true,
      owner: server.owner,
      updatedAt: 0,
      syncedAt: null,
      restored: hasContent(payload),
    }
  }

  if (local && local.updatedAt > (local.syncedAt ?? 0)) {
    return {
      ...base,
      name: local.key,
      payload: local.payload,
      // Only its own row: another device's draft for the same target is not this one's.
      saved: Boolean(local.serverName) || server?.name === local.key,
      updatedAt: local.updatedAt,
      syncedAt: local.syncedAt,
      restored: hasContent(local.payload),
    }
  }

  if (server) {
    const payload = payloadFromDoc(server, seed)
    const now = Date.now()
    return {
      ...base,
      name: server.name,
      payload,
      saved: true,
      updatedAt: now,
      syncedAt: now,
      restored: hasContent(payload),
      needsLocalWrite: true,
    }
  }

  if (local) {
    return {
      ...base,
      name: local.key,
      payload: local.payload,
      saved: Boolean(local.serverName),
      updatedAt: local.updatedAt,
      syncedAt: local.syncedAt,
      restored: hasContent(local.payload),
    }
  }

  return {
    ...base,
    name: input.opened ?? input.name,
    payload: seed,
    saved: false,
    owner: input.opened ? null : sessionUser,
    updatedAt: 0,
    syncedAt: null,
  }
}

/** Read a server row into a payload shaped like the composer's own: a composer with no
 *  title field must not grow one, or it would push an empty title over a real one. */
function payloadFromDoc(doc: ServerDraftDoc, seed: DraftPayload): DraftPayload {
  const payload: DraftPayload = { content: doc.content ?? '' }
  if ('title' in seed) payload.title = doc.title ?? ''
  if ('project' in seed) payload.project = doc.project ?? null
  return payload
}

export function useDraftSync(options: UseDraftSyncOptions) {
  const { identity, debounceMs = 500, canSave = hasContent, initialPayload, onCreate } = options

  // Per instance, not module-level: these hold the in-flight request, and two composers
  // writing different drafts at once would share one URL and one response.
  const draftDoc = useDoctype('GP Draft')

  /**
   * The composer's buffer, or null until the draft has been resolved.
   *
   * Null rather than a seeded payload on purpose. There is nothing to type into before the
   * stored copies have been looked up, so an edit made in that window cannot exist and
   * cannot be overwritten when the lookup lands. Callers get the same guarantee from the
   * type: an editor bound to `data.content` does not compile until they have handled the
   * null, which is the check every composer has to make anyway.
   */
  const data = ref<DraftPayload | null>(null)
  const saving = ref(false)
  const restored = ref(false)
  // The error from the most recent failed push, cleared by the next success. Doubles as the
  // "are we in a failure streak" flag (so we toast once, not per keystroke) and as the reason
  // a caller like publish() can report when the draft is still unsynced.
  const lastError = ref<unknown>(null)
  // The name the draft was opened by (`?draft=`), or null for a new composition.
  const requestedName = toValue(options.draftName ?? null)
  // The draft's name for its whole life; a singleton's is settled when it is looked up.
  const name = ref(requestedName ?? newDraftName())
  // Whether the server row exists. It is always named `name`, so `serverName` is derived.
  const saved = ref(false)
  const serverName = computed(() => (saved.value ? name.value : null))

  // Last local edit vs last successful push, on THIS device. Drives reconciliation
  // without comparing clocks across machines.
  const updatedAt = ref(0)
  const syncedAt = ref<number | null>(null)
  const dirty = computed(() => updatedAt.value > (syncedAt.value ?? 0))

  // The user who owns this draft, captured when the composer opens. Stamped on every local
  // write so a same-browser account switch can't relabel this composer's draft as the new
  // user (the global session.user can change while this instance is still alive).
  const draftOwner = session.user
  // Who the open draft belongs to, or null while unknown. A new composition is ours from
  // the start; a draft opened by name is not known to be ours until the lookup says so.
  // Until then, and for anyone else's shared draft, it is read-only: nothing may save it.
  const owner = ref<string | null>(requestedName ? null : draftOwner)
  const readOnly = computed(() => owner.value === null || owner.value !== draftOwner)
  const isSingleton = computed(() => {
    const id = toValue(identity)
    return id.mode === 'Edit' || Boolean(id.referenceName)
  })

  const isEnabled = () => toValue(options.enabled ?? true)
  const isLoading = computed(() => isEnabled() && data.value === null)

  const seed = (): DraftPayload => (initialPayload ? initialPayload() : { content: '' })

  // Suppress the change-watcher while we write a payload the user did not type: a sibling
  // tab's copy, or the blank buffer left behind by a finished draft.
  const applying = ref(false)
  function applyPayload(payload: DraftPayload) {
    applying.value = true
    data.value = payload
    nextTick(() => {
      applying.value = false
    })
  }

  // `onCreate` is told a new draft's name once, when it is first saved here.
  let announced = Boolean(requestedName)
  async function persistLocal() {
    if (!data.value) return
    const record: DraftRecord = {
      key: name.value,
      identity: toValue(identity),
      payload: { ...data.value },
      serverName: serverName.value,
      updatedAt: updatedAt.value,
      syncedAt: syncedAt.value,
      user: draftOwner,
    }
    await putDraftRecord(record)
    broadcastDraftChange(record.key)
    if (!announced && record.key === name.value) {
      announced = true
      onCreate?.(record.key)
    }
  }

  let activePush: Promise<void> | null = null

  async function persistToServer() {
    const payload = data.value
    if (!payload || readOnly.value || !isEnabled() || !dirty.value || !canSave(payload)) return
    // The edit is already in IndexedDB. Pushing now would only fail and toast; the
    // reconnect handler below sends it once the network is back.
    if (!isOnline.value) return
    // Snapshot what we are about to send, and the edit clock it belongs to, BEFORE the
    // request goes out. Marking the draft synced as of the response time would mark every
    // keystroke typed while the request was in flight as already pushed — those edits go
    // permanently un-synced, and publishing (which builds the discussion from the server
    // row, not the local buffer) then produces a post with an empty body.
    const pushedAt = updatedAt.value
    const draftName = name.value
    const draft = { key: draftName, identity: toValue(identity), payload }
    saving.value = true
    try {
      // The local record says it is saved before the lock is let go: a delete waiting on the
      // lock reads it to know there is a server row to delete.
      const current = await withDraftLock(draftName, async () => {
        await saveToServer(draftDoc, draft, saved.value)
        // Reset onto a new draft meanwhile: this result belongs to the old one.
        if (name.value !== draftName) return false
        saved.value = true
        syncedAt.value = Math.max(syncedAt.value ?? 0, pushedAt)
        await persistLocal()
        return true
      })
      if (current) lastError.value = null
    } catch (error) {
      if (isDeletedError(error)) {
        // Deleted elsewhere, and the server keeps it that way: drop this copy too.
        await deleteDraftRecord(draftName)
        broadcastDraftChange(draftName)
        if (name.value === draftName) reset()
        toast.warning('This draft was deleted, so your changes were not saved.')
        return
      }
      // Keep the local copy; the next edit (or unmount flush) retries, and so does the sweep
      // (recoverOrphanedDrafts), under the same name.
      captureError(error, { action: 'draft-push', draft: draftName })
      // Tell the user once per failure streak so a silently-failing save can't quietly
      // lose server-side persistence. Reset on the next success above.
      if (!lastError.value) {
        toast.error('Could not save your draft to the server — keeping a local copy and retrying.')
      }
      lastError.value = error
    } finally {
      saving.value = false
    }
  }

  // Chain behind an in-flight push rather than joining it: that request was built from an
  // older snapshot, so returning its promise would report edits made since as pushed. The
  // chained run is free when nothing changed — persistToServer() bails on `!dirty`.
  function pushToServer(): Promise<void> {
    const next = (activePush ?? Promise.resolve()).then(persistToServer)
    const push = next.finally(() => {
      if (activePush === push) activePush = null
    })
    activePush = push
    return push
  }

  const debouncedPush = debounce(pushToServer, debounceMs)

  /**
   * Latches on the first edit the person makes, and never clears.
   *
   * Comparing the buffer against the content it started with cannot stand in for this:
   * typing and then deleting it again leaves a buffer identical to the blank one, which
   * is indistinguishable from never having typed at all. Only the late-adopt path below
   * reads it, and only to decline.
   */
  const touched = ref(false)

  watch(
    () => [data.value?.title, data.value?.content, data.value?.project],
    () => {
      // A read-only draft still changes under the editor, which normalizes some content
      // (images, code blocks) on first render. That is not an edit to save.
      if (!data.value || applying.value || readOnly.value || !isEnabled()) return
      touched.value = true
      updatedAt.value = Date.now()
      if (!canSave(data.value)) return
      void persistLocal()
      debouncedPush()
    },
  )

  /** This draft's local record: by name, or for a singleton the newest one for its target. */
  async function findLocalDraft(): Promise<DraftRecord | null> {
    if (!isSingleton.value) return (await getDraftRecord(name.value)) ?? null
    const id = toValue(identity)
    const mine = (await listDraftRecords()).filter(
      (record) => record.user === session.user && isDraftFor(record, id),
    )
    return mine.sort((a, b) => b.updatedAt - a.updatedAt)[0] ?? null
  }

  /** The server row, and whether the server was reached at all. */
  async function fetchServerDraft(
    local: DraftRecord | null,
  ): Promise<{ doc: ServerDraftDoc | null; known: boolean }> {
    try {
      if (isSingleton.value) {
        const id = toValue(identity)
        const doc = await call<ServerDraftDoc | null>(FIND_DRAFT, {
          type: id.type,
          mode: id.mode,
          reference_doctype: id.referenceDoctype,
          reference_name: id.referenceName,
        })
        return { doc, known: true }
      }
      // Never saved, so there is no row to read.
      if (!requestedName || (local && !local.serverName)) return { doc: null, known: true }
      try {
        const doc = await call<ServerDraftDoc>('frappe.client.get', {
          doctype: 'GP Draft',
          name: requestedName,
        })
        return { doc, known: true }
      } catch (error) {
        if (isDeletedError(error)) return { doc: null, known: true }
        // Without the row its owner is unknown, so the draft stays read-only. Say why.
        if (!isNetworkError(error)) {
          toast.error('Could not load this draft. Reload the page to try again.')
        }
        throw error
      }
    } catch (error) {
      // The composer stays usable on a failed lookup, so this is invisible without a report.
      if (!isNetworkError(error)) captureError(error, { action: 'draft-load', draft: name.value })
      return { doc: null, known: false }
    }
  }

  /** Read both stored copies and reconcile them into a starting point. Never rejects. */
  async function lookupDraft(): Promise<ResolvedDraft> {
    try {
      let local = await findLocalDraft()
      const server = await fetchServerDraft(local)
      let opened = requestedName
      let doc = server.doc
      if (server.known && local && doc?.name !== local.key) {
        const unsavedEdits = local.updatedAt > (local.syncedAt ?? 0)
        if (doc && unsavedEdits) {
          // Unsaved edits here beat another tab's or device's row for the same target. They
          // are saved as a draft of their own, and find_my_draft keeps the newest.
          doc = null
        } else if (doc || local.serverName) {
          // Its row is gone (published, deleted, or replaced by a newer reply): so is it.
          await deleteDraftRecord(local.key)
          broadcastDraftChange(local.key)
          if (!doc && local.key === opened) opened = null
          local = null
        }
      }
      return reconcileDraft({
        local,
        server: doc,
        seed: seed(),
        sessionUser: session.user,
        opened,
        name: opened ?? newDraftName(),
      })
    } catch (error) {
      // A composer that cannot reach its draft still has to open, empty and editable.
      captureError(error, { action: 'draft-load', draft: name.value })
      return blankStart()
    }
  }

  /** Where a composer starts when nothing was found, or nothing could be looked up. */
  function blankStart(): ResolvedDraft {
    return reconcileDraft({
      local: null,
      server: null,
      seed: seed(),
      sessionUser: session.user,
      opened: requestedName,
      name: name.value,
    })
  }

  /** Install a resolved draft as the composer's buffer. `quietly` suppresses the change
   *  watcher, for a buffer the user did not type. */
  async function adopt(resolved: ResolvedDraft, { quietly = false } = {}) {
    // A draft other than the one in the URL (a new one, or a deleted one replaced): its name
    // has yet to be handed out.
    if (resolved.name !== requestedName) announced = false
    name.value = resolved.name
    saved.value = resolved.saved
    owner.value = resolved.owner
    updatedAt.value = resolved.updatedAt
    syncedAt.value = resolved.syncedAt
    restored.value = resolved.restored
    if (quietly) applyPayload(resolved.payload)
    else data.value = resolved.payload
    if (resolved.needsLocalWrite) await persistLocal()
  }

  /**
   * Look up the stored copies, reconcile them, and hand the composer its buffer.
   *
   * The buffer is created FROM the result rather than written INTO beforehand, so there is
   * no window in which the lookup and the person typing both own `data`. Runs once; the
   * in-flight promise is shared so a second caller waits rather than starting a second
   * lookup — and it is bounded, so a lookup that hangs cannot strand the composer.
   */
  let opening: Promise<void> | null = null
  function open(): Promise<void> {
    if (data.value) return Promise.resolve()
    if (opening) return opening
    opening = (async () => {
      const pending = lookupDraft()
      const resolved = await Promise.race([pending, timeout(RESOLVE_TIMEOUT_MS)])
      if (resolved) {
        await adopt(resolved)
        return
      }
      // Past the deadline with the lookup still outstanding. Open blank and editable rather
      // than leave the composer inert, and take the result later if it lands on a buffer
      // nobody has touched. The blank goes in quietly so opening the composer does not
      // itself count as an edit; from here `touched` belongs to the person typing.
      captureError(new Error('Draft lookup timed out'), {
        action: 'draft-load',
        draft: name.value,
      })
      const blank = blankStart()
      await adopt(blank, { quietly: true })
      void pending.then((late) => {
        // Identity as well as `touched`, because a buffer swapped out wholesale — by a
        // sibling tab, or by a finished draft — is not this one to overwrite either.
        // `toRaw`, because the ref hands back a reactive proxy, never the object it was given.
        if (touched.value || toRaw(data.value) !== blank.payload) return
        return adopt(late, { quietly: true })
      })
    })()
    return opening
  }

  watch(
    () => isEnabled(),
    (enabled) => {
      if (enabled) void open()
    },
    { immediate: true },
  )

  // Keep sibling tabs of the same draft coherent — but never clobber un-pushed edits
  // typed in this tab.
  const unsubscribe = onDraftChange(async (changedKey) => {
    if (changedKey !== name.value || !data.value) return
    const record = await getDraftRecord(name.value)
    // Deleted, published or posted in another tab: this draft is gone.
    if (!record) return reset()
    if (dirty.value) return
    // Same owner guard as reconcileDraft: on a shared browser the record may be another
    // account's, and we must not pull their content into this editor.
    if (record.user === session.user) {
      applyPayload(record.payload)
      saved.value = saved.value || Boolean(record.serverName)
      updatedAt.value = record.updatedAt
      syncedAt.value = record.syncedAt
    }
  })

  function reset() {
    debouncedPush.cancel?.()
    // Whatever is typed next is a new draft.
    name.value = newDraftName()
    announced = false
    saved.value = false
    owner.value = draftOwner
    updatedAt.value = 0
    syncedAt.value = null
    restored.value = false
    applyPayload(seed())
  }

  /** Drop the local copy and reset, leaving the server untouched. Use after a finalize
   *  that already removed the server row (e.g. publish). */
  async function forget() {
    const draftName = name.value
    reset()
    await deleteDraftRecord(draftName)
    broadcastDraftChange(draftName)
  }

  /** Force any pending change to the server now (creating the row if needed). Chains behind
   *  an in-flight push, so on return the server row reflects the local buffer — unless
   *  `dirty` is still true, which means the push failed. */
  async function flush() {
    await open()
    debouncedPush.cancel?.()
    await pushToServer()
    return serverName.value
  }

  /** Whether the server row exists, as far as this tab or any other has heard. */
  async function isOnServer(draftName: string) {
    return saved.value || Boolean((await getDraftRecord(draftName))?.serverName)
  }

  /**
   * Discard the draft entirely: its server row, if any, and the local copy. A draft on the
   * server can only be deleted with the connection; offline this says so and resolves false,
   * keeping the draft. Rejects if the server refused.
   */
  async function clear(): Promise<boolean> {
    debouncedPush.cancel?.()
    if (activePush) await activePush
    const onServer = await isOnServer(name.value)
    if (onServer && refuseOffline()) return false
    await deleteDraft(name.value, onServer)
    reset()
    return true
  }

  /** Finalize an edit/comment draft after its content has been saved onto the target:
   *  migrate attachments server-side, delete the row, drop the local copy. */
  async function commit() {
    debouncedPush.cancel?.()
    if (activePush) await activePush
    const draftName = name.value
    const onServer = await isOnServer(draftName)
    const id = toValue(identity)
    reset()
    await deleteDraftRecord(draftName)
    broadcastDraftChange(draftName)
    if (onServer && id.referenceDoctype && id.referenceName) {
      try {
        await call(COMMIT_DRAFT, {
          name: draftName,
          reference_doctype: id.referenceDoctype,
          reference_name: id.referenceName,
        })
        // commit_draft deletes the row server-side, so drop it from the list here — the
        // doctype APIs never saw the write.
        drafts.removeRow(draftName)
      } catch (error) {
        console.error('Failed to commit draft', error)
      }
    } else if (onServer) {
      // No target to migrate into (shouldn't happen for singletons) — just delete.
      await deleteServerDraft(draftName).catch((error) =>
        console.error('Failed to delete draft', error),
      )
    }
  }

  const unregisterReconnect = onReconnect(() => {
    if (dirty.value && data.value && canSave(data.value)) void pushToServer()
  })

  onScopeDispose(() => {
    unregisterReconnect()
    unsubscribe()
    // Best-effort: push un-synced edits as we leave so nothing is lost on navigation.
    if (dirty.value && data.value && canSave(data.value)) void pushToServer()
  })

  return {
    /** The composer's buffer, or null until the draft has been resolved. */
    data,
    isLoading,
    /** There are local edits not yet pushed to the server. */
    dirty,
    /** Why the last push failed, or null if the last one succeeded. */
    lastError,
    /** A pre-existing draft was found and restored on load. */
    restored,
    /** The draft's name once its server row exists, else null. */
    serverName,
    /** The draft's name: its local key, its `?draft=` and, once saved, its GP Draft name. */
    name,
    /** Who the draft belongs to, or null while unknown. Unless it is the session user, the
     *  draft is read-only and never saved. */
    owner,
    flush,
    clear,
    commit,
    forget,
  }
}

export type DraftSync = ReturnType<typeof useDraftSync>

/** The fields a draft's server row takes from what it is for. */
function identityFields(id: DraftIdentity) {
  const fields: Record<string, unknown> = { type: id.type, mode: id.mode }
  if (id.referenceName) {
    fields.reference_doctype = id.referenceDoctype
    fields.reference_name = id.referenceName
  }
  return fields
}

/** The fields a draft's server row takes from what was typed. */
function payloadFields(payload: DraftPayload) {
  const fields: Record<string, unknown> = { content: payload.content ?? '' }
  if (payload.title !== undefined) fields.title = payload.title ?? ''
  if (payload.project !== undefined) fields.project = payload.project || null
  return fields
}

type DraftDoctype = ReturnType<typeof useDoctype>

/**
 * Saves a draft under its own name: creates the row, or updates it once it exists. Saving
 * twice cannot make a second row (the create fails as a duplicate and becomes an update),
 * so a retry after a lost response or a crash is always safe. Rejects with
 * `DoesNotExistError` if the draft was deleted.
 */
async function saveToServer(
  doctype: DraftDoctype,
  draft: Pick<DraftRecord, 'key' | 'identity' | 'payload'>,
  onServer: boolean,
) {
  if (!onServer) {
    try {
      await createDraft({
        name: draft.key,
        ...identityFields(draft.identity),
        ...payloadFields(draft.payload),
      })
      return
    } catch (error) {
      if (errorType(error) !== 'DuplicateEntryError') throw error
    }
  }
  // setValue writes through the doctype, so the drafts list picks up the new title/content
  // on its own — no refetch.
  const updated = await doctype.setValue.submit({
    name: draft.key,
    ...payloadFields(draft.payload),
  })
  if (!updated) throw new Error('Could not save the draft')
}

/**
 * Deletes a draft: its server row when `onServer` or its record says it has one, then its
 * record. Runs as the draft's only writer, so it never interleaves with a save of it.
 * Rejects if the server row could not be deleted, keeping the draft.
 */
export function deleteDraft(name: string, onServer = false): Promise<void> {
  return withDraftLock(name, async () => {
    const record = await getDraftRecord(name)
    if (onServer || record?.serverName) await deleteServerDraft(name)
    await deleteDraftRecord(name)
    broadcastDraftChange(name)
  })
}

/** Deletes a draft's server row; one already gone counts as deleted. */
async function deleteServerDraft(name: string) {
  try {
    await call('frappe.client.delete', { doctype: 'GP Draft', name })
  } catch (error) {
    if (!isDeletedError(error)) throw error
  }
  drafts.removeRow(name)
}

/** The draft is gone on the server, or was deleted and cannot be saved again. */
function isDeletedError(error: unknown) {
  return errorType(error) === 'DoesNotExistError'
}

/**
 * Saves every draft of this user that has edits the server has not seen: typed offline, or
 * left when a push failed or the composer closed first. Each goes under its own name, so
 * this never guesses which row a draft belongs to. Returns how many were saved.
 */
export async function recoverOrphanedDrafts(): Promise<number> {
  // One tab at a time: two tabs saving the same drafts would only repeat requests.
  return withLock('gp-draft-recovery', async () => {
    const records = await listDraftRecords()
    // Independent drafts, so concurrently: one slow or failing save must not hold up the rest.
    const results = await Promise.allSettled(records.map((record) => saveOrphanedDraft(record)))
    return results.filter((result) => result.status === 'fulfilled' && result.value).length
  })
}

function hasUnsavedEdits(record: DraftRecord) {
  return record.updatedAt > (record.syncedAt ?? 0)
}

/** Save one stranded draft. Returns whether it was saved. */
async function saveOrphanedDraft(record: DraftRecord): Promise<boolean> {
  const id = record.identity
  // The IndexedDB store is origin-wide, so on a shared browser profile it can hold drafts
  // authored by a previously logged-in user. Never save those as the current user — that
  // would surface another account's private content under this one.
  if (record.user !== session.user || !id) return false
  if (id.mode !== 'New' || !hasUnsavedEdits(record) || !hasContent(record.payload)) return false

  // A reply whose parent discussion was deleted or moved out of reach can't be routed to:
  // get_my_drafts drops it because the parent won't resolve. Keep it here until it can be.
  if (id.referenceName && !(await parentDocResolves(id.referenceDoctype, id.referenceName))) {
    return false
  }
  // Likewise a new discussion pinned to a space the user can no longer reach.
  if (
    !id.referenceName &&
    record.payload.project &&
    !(await parentDocResolves('GP Project', record.payload.project))
  ) {
    return false
  }

  return withDraftLock(record.key, async () => {
    // Read again as the only writer: a composer may have saved or deleted it meanwhile.
    const current = await getDraftRecord(record.key)
    if (!current || !hasUnsavedEdits(current)) return false
    try {
      await saveToServer(useDoctype('GP Draft'), current, Boolean(current.serverName))
    } catch (error) {
      if (isDeletedError(error)) {
        // Deleted elsewhere, and the server keeps it that way: drop this copy too.
        await deleteDraftRecord(current.key)
        broadcastDraftChange(current.key)
      } else if (!isNetworkError(error)) {
        captureError(error, { action: 'draft-recovery', draft: current.key })
      }
      return false
    }
    const latest = (await getDraftRecord(current.key)) ?? current
    await putDraftRecord({
      ...latest,
      serverName: current.key,
      syncedAt: Math.max(latest.syncedAt ?? 0, current.updatedAt),
    })
    broadcastDraftChange(current.key)
    return true
  })
}

/** Whether a referenced document still exists and is readable by the current user.
 *  get_value is permission-checked, so a deleted doc or one in a now-inaccessible space
 *  comes back empty — exactly the cases where recovering a reply draft would strand it. */
async function parentDocResolves(
  doctype: string | null | undefined,
  name: string | null | undefined,
): Promise<boolean> {
  if (!doctype || !name) return false
  try {
    const res = await call<{ name?: string } | null>('frappe.client.get_value', {
      doctype,
      filters: { name },
      fieldname: 'name',
    })
    return Boolean(res?.name)
  } catch {
    return false
  }
}
