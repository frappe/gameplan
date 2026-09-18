import { computed } from 'vue'
import { toast, useList } from 'frappe-ui'
import { session } from './session'
import type { GPSpaceSubscription } from '@/types/doctypes'

/**
 * The spaces the session user wants new-discussion notifications from.
 *
 * A `GP Space Subscription` row exists while the toggle is on and is deleted when it goes
 * off, so the whole preference is "is there a row for this space?". The list is scoped to
 * the user's own rows on the server (per_user_state.py); loading every row at once keeps
 * the sidebar's bell glyph and the space menus off the request path.
 */
export const spaceSubscriptions = useList<GPSpaceSubscription>({
  doctype: 'GP Space Subscription',
  fields: ['name', 'project'],
  limit: 1000,
  cacheKey: ['Space Subscriptions', session.user ?? ''],
  immediate: true,
})

const subscriptionByProject = computed(
  () => new Map((spaceSubscriptions.data ?? []).map((row) => [String(row.project), row])),
)

export function isSpaceNotifying(project: string | number) {
  return subscriptionByProject.value.has(String(project))
}

const toggleToastId = 'space-notifications-toggle'

/**
 * Flip the toggle for one space. The list refetches itself after the write, so the
 * glyph and the switch follow the server's answer rather than a local guess.
 */
export async function toggleSpaceNotifications(project: string | number) {
  const row = subscriptionByProject.value.get(String(project))
  try {
    if (row) {
      await spaceSubscriptions.delete.submit({ name: row.name })
      toast.success('You will no longer be notified about new discussions here', {
        id: toggleToastId,
      })
    } else {
      await spaceSubscriptions.insert.submit({ project: String(project) })
      toast.success('You will be notified about new discussions here', { id: toggleToastId })
    }
  } catch {
    toast.error('Could not update space notifications', { id: toggleToastId })
  }
}
