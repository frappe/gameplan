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
  app.mount('#app')
}

if (import.meta.env.DEV) {
  window.$user = useUser
  window.$users = users
  window.$session = session
  window.$frappeRequest = frappeRequest
  window.$router = router
}
