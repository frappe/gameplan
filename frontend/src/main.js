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
  setConfig,
  frappeRequest,
  pageMetaPlugin,
  resourcesPlugin,
} from 'frappe-ui'
import * as Sentry from '@sentry/vue'
import router from './router'
import App from './App.vue'
import './index.css'
import { getPlatform } from './utils'
import { createDialog } from './utils/dialogs'
import { useUser, users } from './data/users'
import { isSessionUser, session } from './data/session'
import { initSocket } from './socket'
import resetDataMixin from './utils/resetDataMixin'

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
setConfig('resourceFetcher', frappeRequest)
setConfig('defaultListUrl', 'gameplan.extends.client.get_list')
app.use(resourcesPlugin)
app.use(pageMetaPlugin)
app.use(router)
app.mixin(resetDataMixin)
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}

app.config.globalProperties.$dialog = createDialog
app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = useUser
app.config.globalProperties.$users = users
app.config.globalProperties.$session = session
app.config.globalProperties.$readOnlyMode = window.read_only_mode
app.config.globalProperties.$platform = getPlatform()
app.config.globalProperties.$isSessionUser = isSessionUser

let socket
if (import.meta.env.DEV) {
  frappeRequest({ url: '/api/method/gameplan.www.g.get_context_for_dev' }).then((values) => {
    for (let key in values) {
      window[key] = values[key]
    }
    window.system_timezone && setConfig('systemTimezone', window.system_timezone)
    socket = initSocket()
    app.config.globalProperties.$socket = socket
    app.mount('#app')
  })
} else {
  window.system_timezone && setConfig('systemTimezone', window.system_timezone)
  socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
}

// sentry error logging
if (import.meta.env.PROD && window.gameplan_frontend_sentry_dsn) {
  Sentry.init({
    app,
    dsn: window.gameplan_frontend_sentry_dsn,
    integrations: [Sentry.browserTracingIntegration({ router })],
    tracesSampleRate: 1.0,
  })
}

if (import.meta.env.DEV) {
  window.$user = useUser
  window.$users = users
  window.$session = session
  window.$dialog = createDialog
  window.$request = request
  window.$frappeRequest = frappeRequest
  window.$router = router
}
