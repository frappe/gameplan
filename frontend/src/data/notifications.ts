import { useCall } from 'frappe-ui'
import { session } from './session'

export let unreadNotifications = useCall({
  cacheKey: 'Unread Notifications Count',
  url: '/api/v2/method/gameplan.api.unread_notifications',
  initialData: 0,
  immediate: session.isAuthenticated,
})
