import { computed, MaybeRef, reactive, ref } from 'vue'
import { useCall } from '@/data/offlineRevalidation'
import { users } from './users'
import router from '@/router'
import { clearOfflineCaches, guardAgainstUserSwitch } from '@/offline'
import { getSessionUserFromCookie } from '@/utils/sessionCookie'

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
    async onSuccess(data) {
      users.reload()
      sessionUser.value = getSessionUserFromCookie()
      session.login.reset()
      // User-scoped cache keys are fixed when the modules load, so a different user needs a
      // full reload. Awaited so the reload can't cut the previous user's cache clear short.
      if ((await guardAgainstUserSwitch(sessionUser.value)).switched) {
        window.location.href = data.default_route || '/'
      } else {
        router.replace(data.default_route || '/')
      }
    },
  }),
  logout: useCall<LogoutResponse>({
    url: '/api/v2/method/logout',
    method: 'POST',
    immediate: false,
    async onSuccess() {
      sessionUser.value = getSessionUserFromCookie()
      // Leave nothing cached for whoever uses this browser next. Awaited so the redirect
      // can't cut the clear short.
      await clearOfflineCaches()
      window.location.href = '/login'
    },
  }),
  user: sessionUser,
  isLoggedIn: computed(() => sessionUser.value != null),
})

export function isSessionUser(user: string) {
  return session.user === user
}
