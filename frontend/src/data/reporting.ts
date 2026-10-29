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
