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
import router from './router'
import App from './App.vue'
import './index.css'
import { dayjs, getPlatform } from '@/utils'
import { createDialog } from './utils/dialogs'
import { createToast } from './utils/toasts'
import { getUser, users } from './data/users'
import { session } from './data/session'
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
app.config.globalProperties.$dayjs = dayjs
app.config.globalProperties.$dialog = createDialog
app.config.globalProperties.$toast = createToast
app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = getUser
app.config.globalProperties.$users = users
app.config.globalProperties.$session = session
app.config.globalProperties.$readOnlyMode = window.read_only_mode
app.config.globalProperties.$platform = getPlatform()
app.config.globalProperties.$isSessionUser = (email) => {
  return getUser().name === email
}

let socket
if (import.meta.env.DEV) {
  frappeRequest({ url: '/api/method/gameplan.www.g.get_context_for_dev' }).then(
    (values) => {
      for (let key in values) {
        window[key] = values[key]
      }
      socket = initSocket()
      app.config.globalProperties.$socket = socket
      app.mount('#app')
    }
  )
} else {
  socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
}

if (import.meta.env.DEV) {
  window.$dayjs = dayjs
  window.$user = getUser
  window.$users = users
  window.$session = session
  window.$dialog = createDialog
  window.$toast = createToast
  window.$request = request
  window.$frappeRequest = frappeRequest
  window.$router = router
}
