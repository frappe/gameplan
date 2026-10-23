import type { GPPoll } from '@/types/doctypes'
import { useSessionUser } from './users'
import { joinedSpaces, type Space } from './spaces'
import { isCommunityBanned, isGuest } from '@/utils/permissions'
import { isAnonymousVisitor } from '@/utils/publicAccess'

export function canReport(
  content:
    | {
        owner?: string | null
        hidden_at?: string | null
        spam_removed_at?: string | null
        deleted_at?: string | null
      }
    | null
    | undefined,
  space: Space | null | undefined,
) {
  const user = useSessionUser()
  return Boolean(
    content &&
    space &&
    !isAnonymousVisitor() &&
    user.name !== content.owner &&
    !content.hidden_at &&
    !content.spam_removed_at &&
    !content.deleted_at &&
    !isCommunityBanned(space.team, user) &&
    (!isGuest(user) || joinedSpaces.data?.includes(String(space.name))),
  )
}

export type Review = {
  name: string
  reference_doctype: string
  reference_name: string
  creation?: string
  decision?: string
}
export type ReviewDetails = {
  review: {
    status: string
    decision?: string
    decision_note?: string
    decided_by?: string
    decided_at?: string
  }
  current: {
    title?: string
    content: string
    version: string
    owner: string
    discussion: string
    project: string
  }
  reports: {
    name: string
    owner: string
    creation: string
    reason: string
    note: string
  }[]
  evidence: { name: string; reported_title?: string; reported_content: string } | null
  polls: GPPoll[]
  has_more: boolean
}
