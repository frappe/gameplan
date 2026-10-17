import { useList } from 'frappe-ui'
import type { GPCustomEmoji } from '@/types/doctypes'
import { isAnonymousVisitor } from '@/utils/publicAccess'

export type CustomEmoji = Pick<GPCustomEmoji, 'name' | 'title' | 'image' | 'keywords' | 'owner'>

/**
 * Workspace-wide custom emoji library. Readable by everyone (so the picker can
 * show them); only admins can create/delete (enforced by doctype permissions).
 */
export const customEmojis = useList<CustomEmoji>({
  doctype: 'GP Custom Emoji',
  fields: ['name', 'title', 'image', 'keywords', 'owner'],
  orderBy: 'creation desc',
  initialData: [],
  cacheKey: 'CustomEmojis',
  limit: 999,
  // Signed-in only: someone who is not signed in sees custom emoji as the images they are.
  immediate: !isAnonymousVisitor(),
})
