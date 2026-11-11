import { createApp } from 'vue'
import {
  Button,
  TextInput,
  ErrorMessage,
  Dialog,
  Badge,
  frappeRequest,
  setConfig,
  useCall,
} from 'frappe-ui'
import router, { prefetchPages } from './router'
import App from './App.vue'
import './index.css'
import { getPlatform } from './utils'
import { useUser, users } from './data/users'
import { isSessionUser, session } from './data/session'
import { initSocket } from './socket'
import { installErrorReporting } from './utils/errorReporting'

// Not FormControl: it imports every input frappe-ui has (date, time, combobox,
// multi-select), so registering it here put all of them in the first download.
let globalComponents = {
  Button,
  TextInput,
  ErrorMessage,
  Dialog,
  Badge,
}
let app = createApp(App)
app.use(router)
router.isReady().then(prefetchPages)
// Installed before anything else runs, so an error thrown during setup is reported too.
installErrorReporting(app, router)
for (let [key, component] of Object.entries(globalComponents)) {
  app.component(key, component)
}

app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = useUser
app.config.globalProperties.$users = users
app.config.globalProperties.$session = session
app.config.globalProperties.$readOnlyMode = window.read_only_mode
app.config.globalProperties.$platform = getPlatform()
app.config.globalProperties.$isSessionUser = isSessionUser

if (import.meta.env.DEV) {
  useCall<Record<string, unknown>>({
    url: '/api/v2/method/gameplan.www.g.get_context_for_dev',
    method: 'POST',
    onSuccess(values) {
      Object.assign(window, values)
      setupApp()
    },
  })
} else {
  setupApp()
}

// Runs once boot values are on `window` (inline script in prod, the dev
// context call above in dev) so frappe-ui gets its full config in one place.
function setupApp() {
  setConfig('resourceFetcher', frappeRequest)
  setConfig('defaultListUrl', 'gameplan.extends.client.get_list')
  setConfig('systemTimezone', window.system_timezone || null)
  // frappe-ui reads the browser timezone through Intl on every dayjsLocal() call when
  // this is unset. A long list formats several timestamps per row, so resolve it once.
  setConfig('localTimezone', Intl.DateTimeFormat().resolvedOptions().timeZone)
  setConfig('maxFileSize', window.max_file_size ? Number(window.max_file_size) : null)
  app.mount('#app')
  // The first page draws without the realtime connection, so its code downloads after.
  router.isReady().then(initSocket)
}

if (import.meta.env.DEV) {
  Object.assign(window, {
    $user: useUser,
    $users: users,
    $session: session,
    $frappeRequest: frappeRequest,
    $router: router,
  })
}
