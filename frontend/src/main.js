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
import UserImage from '@/components/UserImage.vue'
import './index.css'
import { dayjs } from '@/utils'
import { createDialog } from './utils/dialogs'
import { createToast } from './utils/toasts'
import { userInfo, users } from './data/users'
import { session } from './data/session'
import socket from './socket'
import resetDataMixin from './utils/resetDataMixin'
import { getCachedListResource } from 'frappe-ui/src/resources/listResource'
import { getCachedResource } from 'frappe-ui/src/resources/resources'

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
  UserImage,
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

socket.on('refetch_resource', (data) => {
  if (data.cache_key) {
    let resource =
      getCachedResource(data.cache_key) || getCachedListResource(data.cache_key)
    if (resource) {
      resource.reload()
    }
  }
})

if (import.meta.env.DEV) {
  window.$dayjs = dayjs
  window.$user = userInfo
  window.$users = users
  window.$session = session
  window.$dialog = createDialog
  window.$toast = createToast
  window.$request = request
  window.$frappeRequest = frappeRequest
  window.$router = router
}
