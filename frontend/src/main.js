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
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}

app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = useUser
app.config.globalProperties.$users = users
app.config.globalProperties.$session = session
app.config.globalProperties.$readOnlyMode = window.read_only_mode
app.config.globalProperties.$platform = getPlatform()
app.config.globalProperties.$isSessionUser = isSessionUser

let socket
if (import.meta.env.DEV) {
  useCall({
    url: '/api/v2/method/gameplan.www.g.get_context_for_dev',
    method: 'POST',
    onSuccess(values) {
      for (let key in values) {
        window[key] = values[key]
      }
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
 * Plain DOM, because the app must not mount: another account's discussions are still in this
 * browser's storage, and every list would be free to read them.
 */
function showCleanupFailure() {
  let root = document.getElementById('app')
  if (!root) return
  const isDark =
    document.documentElement.getAttribute('data-theme') === 'dark' ||
    (!document.documentElement.getAttribute('data-theme') &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches)

  const textColor = isDark ? '#f5f5f5' : '#171717'
  const subtextColor = isDark ? '#a3a3a3' : '#525252'
  const btnBg = isDark ? '#262626' : '#fff'
  const btnBorder = isDark ? '#404040' : '#d4d4d4'

  root.innerHTML = `
    <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
                font:400 15px/1.5 ui-sans-serif,system-ui,sans-serif;color:${textColor}">
      <div style="max-width:420px;text-align:center">
        <h1 style="margin:0 0 8px;font-size:18px;font-weight:600;color:${textColor}">Couldn't finish switching accounts</h1>
        <p style="margin:0 0 20px;color:${subtextColor}">
          The previous account's data is still saved in this browser, so Gameplan has not opened.
          Reload to try again. If it keeps happening, close the app's other tabs first.
        </p>
        <button id="cleanup-retry"
          style="padding:8px 16px;border-radius:8px;border:1px solid ${btnBorder};background:${btnBg};
                 font:inherit;font-weight:500;color:${textColor};cursor:pointer">Reload</button>
      </div>
    </div>`
  root.querySelector('#cleanup-retry')?.addEventListener('click', () => window.location.reload())
}

function mountApp() {
  app.mount('#app')
  setupOfflineSupport()
  if (session.isLoggedIn) setupOfflineDownloads()
}

if (import.meta.env.DEV) {
  window.$user = useUser
  window.$users = users
  window.$session = session
  window.$frappeRequest = frappeRequest
  window.$router = router
}
