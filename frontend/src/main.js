import { createApp } from 'vue'
import {
  Button,
  Input,
  ErrorMessage,
  Dialog,
  FeatherIcon,
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
import UserInfo from '@/components/UserInfo.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import './index.css'
import { dayjs } from '@/utils'
import { createDialog } from './utils/dialogs'
import { createToast } from './utils/toasts'
import { userInfo, users } from './data/users'
import { session } from './data/session'
import socket from './socket'
import resetDataMixin from './utils/resetDataMixin'

let globalComponents = {
  Button,
  Input,
  ErrorMessage,
  Dialog,
  FeatherIcon,
  Alert,
  Badge,
  UserInfo,
  UserAvatar,
}
let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)
app.use(resourcesPlugin)
app.use(pageMetaPlugin)
app.use(router)
app.mixin(resetDataMixin)
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}
app.config.unwrapInjectedRef = true
app.config.globalProperties.$socket = socket
app.config.globalProperties.$dayjs = dayjs
app.config.globalProperties.$dialog = createDialog
app.config.globalProperties.$toast = createToast
app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = userInfo
app.config.globalProperties.$users = users
app.config.globalProperties.$session = session
app.config.globalProperties.$readOnlyMode = window.read_only_mode
app.config.globalProperties.$isSessionUser = (email) => {
  return userInfo().name === email
}
app.mount('#app')

if (import.meta.env.DEV) {
  window.$dayjs = dayjs
  window.$user = userInfo
  window.$users = users
  window.$session = session
  window.$dialog = createDialog
  window.$toast = createToast
  window.$request = request
  window.$frappeRequest = frappeRequest
}
