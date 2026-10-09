import { useCall } from 'frappe-ui'
import { isAnonymousVisitor } from '@/utils/publicAccess'

interface AppInfo {
  name: string
  logo: string
  title: string
  route: string
}

export const installedApps = useCall<AppInfo[]>({
  url: '/api/v2/method/frappe.apps.get_apps',
  cacheKey: 'apps',
  immediate: !isAnonymousVisitor(),
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
