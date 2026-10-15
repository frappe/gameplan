import { computed, reactive, watch } from 'vue'
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

const requested = reactive(new Map<string, boolean>())

export function isSpaceNotifying(project: string | number) {
  const key = String(project)
  return requested.has(key) ? requested.get(key)! : subscriptionByProject.value.has(key)
}

const toggleToastId = 'space-notifications-toggle'

const inFlight = new Set<string>()

function settle() {
  for (const [project, on] of requested) {
    if (!inFlight.has(project) && subscriptionByProject.value.has(project) === on) {
      requested.delete(project)
    }
  }
}

watch(subscriptionByProject, settle)

async function apply(projects: (string | number)[], on: boolean, message: string) {
  const changing = projects
    .map(String)
    .filter((project) => !inFlight.has(project) && isSpaceNotifying(project) !== on)
  if (!changing.length) return
  changing.forEach((project) => {
    inFlight.add(project)
    requested.set(project, on)
  })
  const results = await Promise.allSettled(
    changing.map((project) => {
      const row = subscriptionByProject.value.get(project)
      return on
        ? spaceSubscriptions.insert.submit({ project })
        : row && spaceSubscriptions.delete.submit({ name: row.name })
    }),
  )
  if (results.some((result) => result.status === 'rejected')) {
    toast.error('Could not update space notifications', { id: toggleToastId })
    await spaceSubscriptions.reload().catch(() => {})
    changing.forEach((project) => requested.delete(project))
  } else {
    toast.success(message, { id: toggleToastId })
  }
  changing.forEach((project) => inFlight.delete(project))
  settle()
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
