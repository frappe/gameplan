import { createApp } from 'vue'
import {
  Button,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  frappeRequest,
  FrappeUI,
  setConfig,
  useCall,
} from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './index.css'
import { getPlatform } from './utils'
import { useUser, users } from './data/users'
import { isSessionUser, session } from './data/session'
import { initSocket } from './socket'
import { installErrorReporting } from './utils/errorReporting'
import resetDataMixin from './utils/resetDataMixin'
import { clearCachesOnUserSwitch, setupOfflineSupport } from './offline'
import { setupOfflineDownloads } from './data/offlineDownloads'
import CleanupFailure from './components/CleanupFailure.vue'

let globalComponents = {
  Button,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
}
let app = createApp(App)
app.use(router)
// Installed before anything else runs, so an error thrown during setup is reported too.
installErrorReporting(app, router)
app.mixin(resetDataMixin)
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

let socket: ReturnType<typeof initSocket>
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
  // `resources: true` keeps the v1 resources Options API installed for
  // UnsplashImageBrowser.vue and People.vue, the last two components declaring
  // a `resources` option. Port both to createResource/useList to drop this.
  app.use(FrappeUI, { resources: true })
  setConfig('resourceFetcher', frappeRequest)
  setConfig('defaultListUrl', 'gameplan.extends.client.get_list')
  setConfig('systemTimezone', window.system_timezone || null)
  setConfig('maxFileSize', window.max_file_size ? Number(window.max_file_size) : null)
  socket = initSocket()
  app.config.globalProperties.$socket = socket
  // A switched user's data goes before the first component can read it. If it could not be
  // cleared, this browser still holds the previous account's content, so nothing is shown.
  clearCachesOnUserSwitch().then((safe) => (safe ? mountApp() : showCleanupFailure()))
}

/**
 * Isolated recovery UI using Frappe UI, because the main app must not mount: another account's
 * discussions are still in this browser's storage, and every list would be free to read them.
 */
function showCleanupFailure() {
  if (!document.getElementById('app')) return
  createApp(CleanupFailure).mount('#app')
}

function mountApp() {
  app.mount('#app')
  setupOfflineSupport()
  if (session.isLoggedIn) setupOfflineDownloads()
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
