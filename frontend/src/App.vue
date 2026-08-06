<template>
  <FrappeUIProvider>
    <div class="relative isolate h-full overflow-hidden">
      <router-view v-if="['Onboarding', 'Login'].includes($route.name)" />
      <Layout v-else-if="$session.isLoggedIn">
        <!-- While on a /settings/* URL, keep rendering the page the dialog was
             opened over (displayedRoute) so it stays visible behind the overlay. -->
        <router-view :route="displayedRoute" />
      </Layout>
    </div>
    <NewTaskDialog />
    <!-- usersReady, not users.isFinished: a mid-session reload of the user list would
         flip isFinished back to false and unmount the open settings dialog. -->
    <SettingsDialog v-if="$session.isLoggedIn && usersReady" />
    <component :is="DevUserSwitcher" v-if="DevUserSwitcher && $session.isLoggedIn && usersReady" />
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, shallowRef, watch } from 'vue'
import { loadRouteLocation, useRoute, useRouter } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import { users, usersReady } from '@/data/users'
import { session } from '@/data/session'
import { useScreenSize } from 'frappe-ui'
import { useTheme } from '@/utils/useTheme'
import { useCursorStyle } from '@/utils/useCursorStyle'
import NewTaskDialog from './components/NewTaskDialog/NewTaskDialog.vue'
import SettingsDialog from './components/Settings/SettingsDialog.vue'
import { settingsBackgroundPath } from './components/Settings'
import { getHomeRoute } from '@/router'

const screenSize = useScreenSize()
const route = useRoute()
const router = useRouter()
useTheme()
useCursorStyle()
// `import.meta.env.DEV` is a compile-time constant, so a production build folds
// this to null and drops the dynamic import — the switcher is never bundled.
const DevUserSwitcher = import.meta.env.DEV
  ? defineAsyncComponent(() => import('./components/DevUserSwitcher.vue'))
  : null
const MobileLayout = defineAsyncComponent(() => import('./components/MobileLayout.vue'))
const DesktopLayout = defineAsyncComponent(() => import('./components/DesktopLayout.vue'))
const Layout = computed(() => {
  if (screenSize.width < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

users.fetch()

const isSettingsOverlay = (r) => r.matched.some((record) => record.meta?.settingsOverlay)

// A resolved-but-never-navigated route still holds its lazy `() => import()`
// components unresolved, which <router-view :route> renders as "[object Promise]"
// (hit on a cold load / reload of a settings URL). loadRouteLocation() forces
// those imports to resolve before we hand the route to the view.
const isRouteLoaded = (target) =>
  target.matched.every((record) =>
    Object.values(record.components ?? {}).every((component) => typeof component !== 'function'),
  )

// On a /settings/* URL, render the page the dialog was opened over (or Home on a
// cold load) behind the overlay; otherwise render the current route normally.
//
// shallowRef (not ref): a route object holds its matched components, and deep
// reactivity would wrap those component definitions in a Proxy ("received a
// Component that was made into a reactive object" warning).
const displayedRoute = shallowRef(route)
watch(
  [() => route.fullPath, settingsBackgroundPath],
  () => {
    if (!isSettingsOverlay(route)) {
      displayedRoute.value = route
      return
    }
    const target = router.resolve(settingsBackgroundPath.value || getHomeRoute())
    // Point the view at the background page SYNCHRONOUSLY. `useRoute()` hands back one
    // live object whose properties are getters onto the router's current route, so
    // `displayedRoute` aliases it — yielding here (even for one microtask) lets the main
    // <router-view> render the /settings route first. Its only component is the no-op
    // RouteGuard, so the page behind the overlay is unmounted and then rebuilt a tick
    // later while the URL still says /settings. Pages that canonicalise their own URL on
    // mount then rewrite it off /settings and the dialog closes the frame it appeared.
    if (isRouteLoaded(target)) {
      displayedRoute.value = target
      return
    }
    // Cold load / reload on a /settings URL: no page is mounted yet, so there is nothing
    // to tear down and waiting for the lazy chunks is safe.
    loadRouteLocation(target).then(() => {
      // Closing the dialog nulls settingsBackgroundPath (router guard) a tick before
      // the URL leaves /settings, so this watcher can start resolving a background
      // page (falling back to Home) while still on the settings route. If the
      // overlay has since closed, the non-overlay branch already set the real route
      // — don't let this stale async result clobber it back to Home.
      if (!isSettingsOverlay(route)) return
      displayedRoute.value = target
    })
  },
  { immediate: true },
)

// Back-compat: ?settings=notifications deep links now redirect to the canonical
// settings URL.
watch(
  () => [route.query.settings, session.isLoggedIn, usersReady.value],
  async ([settings]) => {
    if (settings !== 'notifications' || !session.isLoggedIn || !usersReady.value) return

    await nextTick()
    router.replace({ name: 'SettingsTab', params: { tab: 'notifications' } })
  },
  { immediate: true },
)
</script>
