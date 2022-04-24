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
} from 'frappe-ui'
import router from './router'
import App from './App.vue'
import UserInfo from '@/components/UserInfo.vue'
import './index.css'
import { dayjs } from '@/utils'
import { createDialog } from './utils/dialogs'

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
app.config.globalProperties.$log = console.log.bind(console)
app.use(router)
app.mount('#app')
