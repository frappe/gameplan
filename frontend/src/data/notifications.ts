import { useCall } from 'frappe-ui'
import { useDebounceFn } from '@vueuse/core'
import type { RouteLocationRaw } from 'vue-router'
import { onSocketEvent, type NotificationChange } from '@/socket'
import type { GPNotification } from '@/types/doctypes'
import { getCommunity } from './communities'
import { getSpace } from './spaces'

export let unreadNotifications = useCall({
  cacheKey: 'Unread Notifications Count',
  url: '/api/v2/method/gameplan.api.unread_notifications',
  initialData: 0,
})

const listeners = new Set<() => void>()

/**
 * What this tab last saw of each notification row, keyed by name. Fed by the pages that
 * render rows (`rememberNotificationRows`) and read by the socket handler below to tell a
 * genuine change from the echo of this tab's own write.
 */
const lastSeen = new Map<string, { event_count: number; read: 0 | 1 }>()

/**
 * Record the rows a list just loaded, so a later `notification_changed` event naming one
 * of them can be recognised as already-known. Call it from every list `onSuccess`.
 */
export function rememberNotificationRows(
  rows: Array<{ name: string; event_count?: number; read?: 0 | 1 | boolean }> | null | undefined,
) {
  for (const row of rows ?? []) {
    lastSeen.set(row.name, {
      event_count: row.event_count ?? 1,
      read: row.read ? 1 : 0,
    })
  }
}

/**
 * Run `handler` when this user's notifications changed into something this tab is not
 * already showing — a new row, a merge that bumped a row's count, or a row read or cleared
 * elsewhere. Returns an unsubscribe function.
 *
 * The backend signals this user on every change, from any tab or device, this one
 * included. An event this tab caused is pure duplication: the tab has already reloaded
 * itself, so acting on the echo doubles the requests per click and aborts the reload still
 * in flight, which frappe-ui's fetch wrapper reports as an AbortError.
 *
 * The echo is told apart by *what it reports*, not by when it arrives. The event carries the
 * changed row (see gameplan/realtime.py); a row this tab already holds with the same
 * `event_count` and `read` says nothing this tab does not know. Anything else is news: a
 * row never seen here, a merge that moved its count, a read flag flipped elsewhere, or a
 * bulk clear (`notification: null`). The unread total alone could not carry that — a repeat
 * event merging into an already-unread row leaves the total exactly where it was — and a
 * clock cannot decide it: clicking a notification marks it read here and, one navigation
 * later, has `track_visit` clear the rest of that thread on the server, so a window wide
 * enough to cover the echo swallowed that real change and left the badge too high.
 */
export function onRemoteNotificationChange(handler: () => void) {
  listeners.add(handler)
  return () => {
    listeners.delete(handler)
  }
}

/**
 * True when the event's row tells this tab something it does not already show. A bulk
 * clear carries no row; for it the unread total is the whole story, so it is never news on
 * its own — a clear that moved nothing is an echo.
 */
function rowIsNews(notification: NotificationChange | null) {
  if (!notification) return false
  const seen = lastSeen.get(notification.name)
  return !seen || seen.event_count !== notification.event_count || seen.read !== notification.read
}

// One subscription, so every listener acts on the same set of events. Deciding per listener
// would race: whichever ran first would reload the badge and change the answer for the rest.
onSocketEvent(
  'gameplan:notification_changed',
  useDebounceFn(({ count, notification }) => {
    const countMoved = count !== unreadNotifications.data
    if (!countMoved && !rowIsNews(notification)) return
    // Reloaded rather than taken from the event: `data` is a computed inside useCall, and a
    // single fetched count keeps the badge and the lists reading the same server state.
    if (countMoved) unreadNotifications.reload()
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

/** The columns a notification row needs to be shown, routed and marked read. */
export type NotificationRow = Pick<
  GPNotification,
  | 'name'
  | 'type'
  | 'message'
  | 'from_user'
  | 'discussion'
  | 'comment'
  | 'poll'
  | 'task'
  | 'project'
  | 'team'
  | 'read'
  | 'event_count'
> & { last_event_at: string }

/** Where a row opens: its discussion, task, space or community. */
export function notificationRoute(
  notification: Omit<NotificationRow, 'read' | 'last_event_at' | 'message' | 'event_count'>,
): RouteLocationRaw | null {
  if (notification.discussion) {
    return {
      name: 'Discussion',
      params: {
        communityId: notification.team,
        spaceId: notification.project,
        postId: notification.discussion,
      },
      query: notification.poll
        ? { poll: notification.poll }
        : notification.comment
          ? { comment: notification.comment }
          : undefined,
    }
  }
  if (notification.task) {
    return {
      name: 'SpaceTask',
      params: {
        communityId: notification.team,
        spaceId: notification.project,
        taskId: notification.task,
      },
      query: notification.comment ? { comment: notification.comment } : undefined,
    }
  }
  // Added to a space, or a space moved: the space itself. Added to a community: its feed.
  if (notification.project && notification.team) {
    return {
      name: 'Space',
      params: { communityId: notification.team, spaceId: notification.project },
    }
  }
  if (notification.team) {
    return { name: 'Discussions', params: { communityId: notification.team } }
  }
  return null
}

/** The glyph that stands in when a row has no sender avatar to show. */
export function notificationIcon(notification: { type?: string }) {
  if (notification.type === 'Rich Quote') return 'lucide-text-quote'
  // A merged "N new comments" row has no single sender, so no avatar — this stands in.
  if (notification.type === 'Comment') return 'lucide-message-circle'
  if (notification.type === 'New Discussion') return 'lucide-message-square-plus'
  if (notification.type === 'Added') return 'lucide-user-plus'
  if (notification.type === 'Moved') return 'lucide-corner-up-right'
  if (notification.type === 'Poll Vote') return 'lucide-bar-chart-2'
  return 'lucide-at-sign'
}

/** "Community / Space" for a row, from the lists the app already holds. */
export function notificationLocation(notification: {
  team?: string | null
  project?: string | number | null
}) {
  const community = notification.team ? getCommunity(notification.team)?.title : null
  const space = notification.project ? getSpace(String(notification.project))?.title : null
  return [community, space].filter(Boolean).join(' / ')
}
