import { computed } from 'vue'
import { useList } from 'frappe-ui'
import { session } from './session'

/** A row from `get_my_drafts` — a new-discussion draft or a new-comment draft on a
 *  discussion, already resolved to everything needed to render and route it. */
export interface DraftRow {
  name: string
  kind: 'discussion' | 'comment'
  owner: string
  title: string | null
  content: string | null
  modified: string
  creation: string
  space: string | null
  space_title: string | null
  community: string | null
  is_private: boolean | number
  /** For comment drafts, the parent discussion to open; null for discussion drafts. */
  discussion: string | null
}

/**
 * One enriched, route-ready feed of the user's new drafts — discussions and comment
 * replies alike. The backend resolves comment drafts' parent discussion + space, which
 * the bare GP Draft row can't express, so `url` points the list at that method instead of
 * the plain document endpoint.
 *
 * It is still a `useList` on `GP Draft`, which is what keeps it current: the list registers
 * under its doctype, so any `useDoc`/`useDoctype` write on a GP Draft — the composer
 * deleting a draft, a debounced content push — updates or drops the matching row here with
 * no refetch, and `drafts.insert` adds a new one. Creating and deleting a draft happens in
 * the composer, far from this feed; as a bare fetch it went stale until a page reload.
 *
 * Shared rather than page-local: the rail counts these in a tooltip, so it has to outlive
 * the Drafts page.
 */
export const drafts = useList<DraftRow>({
  doctype: 'GP Draft',
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts',
  // The method returns every draft the user owns, so paging is the list's own concern only.
  limit: 999,
  // get_my_drafts is owner-scoped on the server; scope the client cache to the session user
  // too, so a same-tab account switch can't briefly show the previous user's draft rows.
  cacheKey: ['drafts', session.user],
  immediate: true,
})

export const draftCount = computed(() => drafts.data?.length ?? 0)

/**
 * Create a `GP Draft` through the list that owns it, so the new row appears here (and in the
 * rail count) as soon as the server has it.
 *
 * Serialized because `drafts.insert` is a single shared request: two composers creating their
 * first draft at the same moment would otherwise read each other's response and bind to the
 * wrong draft name.
 */
let insertQueue: Promise<unknown> = Promise.resolve()

export function createDraft(fields: Record<string, unknown>): Promise<DraftDoc> {
  const next = insertQueue.then(async () => {
    const doc = (await drafts.insert.submit(fields as Partial<DraftRow>)) as DraftDoc | null
    // useCall resolves with null instead of rejecting; callers rely on a throw to keep their
    // local copy and retry.
    if (!doc?.name) throw new Error('Could not create the draft')
    return doc
  })
  insertQueue = next.catch(() => {})
  return next
}

/** The bare `GP Draft` row an insert returns — not the enriched {@link DraftRow} the list holds. */
interface DraftDoc {
  name: string
}
