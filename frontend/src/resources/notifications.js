import { createResource } from 'frappe-ui'

export let unreadNotifications = createResource({
  cache: 'Unread Notifications Count',
  method: 'gameplan.api.unread_notifications',
  initialData: 0,
})
unreadNotifications.fetch()
