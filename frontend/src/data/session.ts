import { computed, MaybeRef, reactive, ref } from 'vue'
import { useCall } from 'frappe-ui'
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

export let sessionUser = ref<string>(getSessionUserFromCookie())

export let session = reactive({
  user: sessionUser,
  isAnonymous: computed(() => sessionUser.value === 'Guest'),
  isAuthenticated: computed(() => sessionUser.value !== 'Guest'),
  isLoggedIn: computed(() => sessionUser.value !== 'Guest'),
  canBrowsePublicWeb: computed(
    () =>
      sessionUser.value === 'Guest' &&
      Boolean(window.gameplan_public_web_enabled && window.is_public_visitor),
  ),
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
    method: 'POST',
    immediate: false,
    onSuccess() {
      sessionUser.value = getSessionUserFromCookie()
      window.location.href = '/login'
    },
  }),
})

export function isSessionUser(user: string) {
  return session.user === user
}

function getSessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  return cookies.get('user_id') || 'Guest'
}
