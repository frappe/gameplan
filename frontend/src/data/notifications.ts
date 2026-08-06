import { useCall } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import { onSocketEvent } from '@/socket'

export let unreadNotifications = useCall({
  cacheKey: 'Unread Notifications Count',
  url: '/api/v2/method/gameplan.api.unread_notifications',
  initialData: 0,
})

const listeners = new Set<() => void>()

/**
 * Run `handler` when this user's unread notifications changed into something this tab is
 * not already showing — a new notification, or one read or cleared elsewhere. Returns an
 * unsubscribe function.
 *
 * The backend signals this user on every change, from any tab or device, this one
 * included. An event this tab caused is pure duplication: the tab has already reloaded
 * itself, so acting on the echo doubles the requests per click and aborts the reload still
 * in flight, which frappe-ui's fetch wrapper reports as an AbortError.
 *
 * The echo is told apart by *what it reports*, not by when it arrives: the event carries
 * the user's current unread count (see gameplan/realtime.py), and an event naming the
 * count the badge already shows says nothing this tab does not know. A clock cannot decide
 * this — clicking a notification marks it read here and, one navigation later, has
 * `track_visit` clear the rest of that thread on the server, so a window wide enough to
 * cover the echo swallowed that real change and left the badge too high.
 *
 * Losing an event whose count matches by coincidence — one notification read elsewhere
 * while another arrives — is the whole cost, and it leaves the badge correct and only the
 * open list stale until the next change.
 */
export function onRemoteNotificationChange(handler: () => void) {
  listeners.add(handler)
  return () => {
    listeners.delete(handler)
  }
}

// One subscription, so every listener acts on the same set of events. Deciding per listener
// would race: whichever ran first would reload the badge and change the answer for the rest.
onSocketEvent(
  'gameplan:notification_count_changed',
  useDebounceFn(({ count }) => {
    if (count === unreadNotifications.data) return
    // Reloaded rather than taken from the event: `data` is a computed inside useCall, and a
    // single fetched count keeps the badge and the lists reading the same server state.
    unreadNotifications.reload()
    for (const handler of [...listeners]) {
      try {
        handler()
      } catch (error) {
        // One bad listener must not skip the rest.
        console.error('Notification change listener failed', error)
      }
    }
  }, 500),
)
