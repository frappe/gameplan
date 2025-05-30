import { computed, MaybeRef, reactive, ref } from 'vue'
import { useCall } from 'frappe-ui/src/data-fetching'
import { users } from './users'
import router from '@/router'

interface LoginResponse {
  user: string
  default_route?: string
}

interface LoginParams {
  usr: MaybeRef<string>
  pwd: MaybeRef<string>
}

type LogoutResponse = void

export let sessionUser = ref<string | null>(getSessionUserFromCookie())

export let session = reactive({
  login: useCall<LoginResponse, LoginParams>({
    url: '/api/v2/method/login',
    immediate: false,
    onSuccess(data) {
      users.reload()
      sessionUser.value = getSessionUserFromCookie()
      session.login.reset()
      router.replace(data.default_route || '/')
    },
  }),
  logout: useCall<LogoutResponse>({
    url: '/api/v2/method/logout',
    immediate: false,
    onSuccess() {
      sessionUser.value = getSessionUserFromCookie()
      window.location.href = '/login'
    },
  }),
  user: sessionUser,
  isLoggedIn: computed(() => sessionUser.value != null),
})

export function isSessionUser(user: string) {
  return session.user === user
}

function getSessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  let _sessionUser = cookies.get('user_id')
  if (_sessionUser === 'Guest') {
    _sessionUser = null
  }
  return _sessionUser
}
