import { useCall } from 'frappe-ui'
import { onSocketEvent } from '@/socket'

export let unreadNotifications = useCall({
  cacheKey: 'Unread Notifications Count',
  url: '/api/v2/method/gameplan.api.unread_notifications',
  initialData: 0,
})

// Keeps the rail badge live: the backend signals this user whenever a notification is created
// for them or their notifications are marked read, including from another tab or device.
onSocketEvent('gameplan:notification_count_changed', () => {
  unreadNotifications.reload()
})
