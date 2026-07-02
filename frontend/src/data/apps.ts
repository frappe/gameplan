import { useCall } from 'frappe-ui'
import { session } from './session'

interface AppInfo {
  name: string
  logo: string
  title: string
  route: string
}

export const installedApps = useCall<AppInfo[]>({
  url: '/api/v2/method/frappe.apps.get_apps',
  cacheKey: 'apps',
  immediate: session.isAuthenticated,
  transform(data) {
    let _apps = [
      {
        name: 'frappe',
        logo: '/assets/frappe/images/framework.png',
        title: 'Desk',
        route: '/app',
      },
    ]
    data.forEach((app) => {
      if (app.name === 'gameplan') return
      _apps.push(app)
    })

    return _apps
  },
})
