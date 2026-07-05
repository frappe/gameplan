import { createApp } from 'vue'
import {
  Button,
  Input,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  request,
  frappeRequest,
  pageMetaPlugin,
  FrappeUI,
  useCall,
} from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './index.css'
import { getPlatform } from './utils'
import { useUser, users } from './data/users'
import { isSessionUser, session } from './data/session'
import { initSocket } from './socket'
import resetDataMixin from './utils/resetDataMixin'
import { setupOfflineSupport } from './offline'

let globalComponents = {
  Button,
  TextInput,
  Input,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
}
let app = createApp(App)
app.use(pageMetaPlugin)
app.use(router)
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
  app.use(FrappeUI, {
    call: false,
    socketio: false,
    config: {
      resourceFetcher: frappeRequest,
      defaultListUrl: 'gameplan.extends.client.get_list',
      systemTimezone: window.system_timezone || null,
      maxFileSize: window.max_file_size ? Number(window.max_file_size) : null,
    },
  })
  socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
  setupOfflineSupport()
}

// Sentry error logging. Loaded lazily (dynamic import) so the ~250 KB SDK stays
// out of the entry chunk — it's the #1 resource on the initial critical path and
// is only ever needed in production when a DSN is configured. The import fires
// during setup so browser-tracing still attaches early enough to capture vitals.
if (import.meta.env.PROD && window.gameplan_frontend_sentry_dsn) {
  import('@sentry/vue').then((Sentry) => {
    Sentry.init({
      app,
      dsn: window.gameplan_frontend_sentry_dsn,
      integrations: [Sentry.browserTracingIntegration({ router })],
      tracesSampleRate: 1.0,
    })
  })
}

if (import.meta.env.DEV) {
  window.$user = useUser
  window.$users = users
  window.$session = session
  window.$request = request
  window.$frappeRequest = frappeRequest
  window.$router = router
}
