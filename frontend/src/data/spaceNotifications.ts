import { computed } from 'vue'
import { toast, useList } from 'frappe-ui'
import { session } from './session'
import type { GPSpaceSubscription } from '@/types/doctypes'

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

// A space whose row is still being written or deleted. The list only learns the new state
// when the request lands, so without this a second click reads the old state and asks for
// the same change again — and (user, project) is unique, so the duplicate insert throws.
const inFlight = new Set<string>()

async function apply(projects: (string | number)[], on: boolean, message: string) {
  const changing = projects
    .map(String)
    .filter((project) => !inFlight.has(project) && isSpaceNotifying(project) !== on)
  if (!changing.length) return
  changing.forEach((project) => inFlight.add(project))
  try {
    await Promise.all(
      changing.map((project) => {
        const row = subscriptionByProject.value.get(project)
        return on
          ? spaceSubscriptions.insert.submit({ project })
          : row && spaceSubscriptions.delete.submit({ name: row.name })
      }),
    )
    toast.success(message, { id: toggleToastId })
  } catch {
    // The row may have gone on the server already — losing the space takes its
    // subscriptions with it — leaving this list showing a bell that no longer exists.
    // Re-reading it puts the control back in step with what is actually stored.
    await spaceSubscriptions.reload()
    toast.error('Could not update space notifications', { id: toggleToastId })
  } finally {
    changing.forEach((project) => inFlight.delete(project))
  }
}

export function toggleSpaceNotifications(project: string | number) {
  const on = !isSpaceNotifying(project)
  return apply(
    [project],
    on,
    on
      ? 'You will be notified about new discussions here'
      : 'You will no longer be notified about new discussions here',
  )
}

export function setSpaceNotifications(projects: (string | number)[], on: boolean) {
  return apply(
    projects,
    on,
    on
      ? 'You will be notified about new discussions in these spaces'
      : 'You will no longer be notified about new discussions in these spaces',
  )
}
