import { computed } from 'vue'
import { useCall } from 'frappe-ui'
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
 * the bare GP Draft row can't express, so the client just renders and routes.
 *
 * Shared rather than page-local: the rail counts these in a tooltip, so the fetch has to
 * outlive the Drafts page.
 */
export const drafts = useCall<DraftRow[]>({
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_draft.gp_draft.get_my_drafts',
  method: 'POST',
  // get_my_drafts is owner-scoped on the server; scope the client cache to the session user
  // too, so a same-tab account switch can't briefly show the previous user's draft rows.
  cacheKey: ['drafts', session.user],
  immediate: true,
})

export const draftCount = computed(() => drafts.data?.length ?? 0)
