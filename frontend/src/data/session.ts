import { computed, MaybeRef, reactive, ref } from 'vue'
import { useCall } from 'frappe-ui'
import { users } from './users'
import router from '@/router'
import { clearOfflineCaches, guardAgainstUserSwitch } from '@/offline'

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
      // Every user-scoped cacheKey in the data layer (communities, users, drafts) was
      // computed once at module-eval time from whichever user (or Guest) was signed in
      // when this tab first loaded - logging in as someone else here doesn't rebuild
      // them. A plain router.replace would keep those singletons around, so force a full
      // reload once a switch is detected and let the app rebuild everything fresh for
      // the new user (same reasoning as DevUserSwitcher.vue's own hard reload).
      //
      // Awaited (PR #516 review round 4 finding): guardAgainstUserSwitch's cache clear
      // used to be fire-and-forget, so this redirect could tear the page down before the
      // previous user's SHELL_CACHE/IndexedDB were actually wiped - the switch marker
      // would already say "handled" while the old data was still sitting there for the
      // next offline load to serve. Waiting here means the hard-navigate below only
      // happens once the clear has actually settled.
      if (await guardAgainstUserSwitch(sessionUser.value)) {
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
      // Shared-computer safety: don't leave this session's cached content behind for
      // whoever logs in next (PR #516). Awaited so the redirect (which tears down this
      // page) doesn't cut the clear short.
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

function getSessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  let _sessionUser = cookies.get('user_id')
  if (_sessionUser === 'Guest') {
    _sessionUser = null
  }
  return _sessionUser
}
