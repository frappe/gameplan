import { createApp } from 'vue'
import {
  FrappeUI,
  Button,
  Input,
  ErrorMessage,
  Dialog,
  FeatherIcon,
  Alert,
  Badge,
  createCall,
  pageMeta,
} from 'frappe-ui'
import router from './router'
import App from './App.vue'
import UserInfo from '@/components/UserInfo.vue'
import './index.css'
import { dayjs } from '@/utils'
import { createDialog } from './utils/dialogs'
import { createToast } from './utils/toasts'
import { userInfo, usersResource } from './data/users'

let globalComponents = {
  Button,
  Input,
  ErrorMessage,
  Dialog,
  FeatherIcon,
  Alert,
  Badge,
  UserInfo,
}

let call = createCall({
  onError({ status }) {
    if (status === 403 && document.cookie.includes('sid=Guest')) {
      console.log('navigate to login')
    }
  },
})

let app = createApp(App)
app.use(FrappeUI, {
  call,
  resources: {
    getResource: call,
  },
})
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}
app.config.globalProperties.$dayjs = dayjs
app.config.globalProperties.$dialog = createDialog
app.config.globalProperties.$toast = createToast
app.config.globalProperties.$log = console.log.bind(console)
app.config.globalProperties.$user = userInfo
app.config.globalProperties.$users = usersResource
app.config.globalProperties.$isSessionUser = (email) => {
  return userInfo().name === email
}
app.use(router)
app.use(pageMeta)

app.mount('#app')

if (import.meta.env.DEV) {
  window.$dayjs = dayjs
  window.$user = userInfo
  window.$users = usersResource
  window.$dialog = createDialog
  window.$toast = createToast
}
