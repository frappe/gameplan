<template>
  <FrappeUIProvider>
    <ScrollAreaRoot class="h-full overflow-hidden">
      <router-view v-if="['Onboarding', 'Login'].includes($route.name)" />
      <Layout v-else-if="session.isLoggedIn || session.canBrowsePublicWeb">
        <!-- While on a /settings/* URL, keep rendering the page the dialog was
             opened over (displayedRoute) so it stays visible behind the overlay. -->
        <router-view :route="displayedRoute" />
      </Layout>
    </ScrollAreaRoot>
    <NewTaskDialog v-if="session.isLoggedIn" />
    <SettingsDialog v-if="session.isLoggedIn && users.isFinished" />
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent, nextTick, shallowRef, watch } from 'vue'
import { loadRouteLocation, useRoute, useRouter } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'
import { ScrollAreaRoot } from 'reka-ui'
import { users } from '@/data/users'
import { session } from '@/data/session'
import { useScreenSize } from '@/composables/useScreenSize'
import { useTheme } from '@/utils/useTheme'
import NewTaskDialog from './components/NewTaskDialog/NewTaskDialog.vue'
import SettingsDialog from './components/Settings/SettingsDialog.vue'
import { settingsBackgroundPath } from './components/Settings'
import { getHomeRoute } from '@/router'

const screenSize = useScreenSize()
const route = useRoute()
const router = useRouter()
useTheme()
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

// On a /settings/* URL, render the page the dialog was opened over (or Home on a
// cold load) behind the overlay; otherwise render the current route normally.
//
// A resolved-but-never-navigated route still holds its lazy `() => import()`
// components unresolved, which <router-view :route> renders as "[object Promise]"
// (hit on a cold load / reload of a settings URL). loadRouteLocation() forces
// those imports to resolve before we hand the route to the view.
//
// shallowRef (not ref): a route object holds its matched components, and deep
// reactivity would wrap those component definitions in a Proxy ("received a
// Component that was made into a reactive object" warning).
const displayedRoute = shallowRef(route)
watch(
  [() => route.fullPath, settingsBackgroundPath],
  async () => {
    if (!route.matched.some((r) => r.meta?.settingsOverlay)) {
      displayedRoute.value = route
      return
    }
    const target = router.resolve(settingsBackgroundPath.value || getHomeRoute())
    await loadRouteLocation(target)
    // Closing the dialog nulls settingsBackgroundPath (router guard) a tick before
    // the URL leaves /settings, so this watcher can start resolving a background
    // page (falling back to Home) while still on the settings route. If the
    // overlay has since closed, the non-overlay branch already set the real route
    // — don't let this stale async result clobber it back to Home.
    if (!route.matched.some((r) => r.meta?.settingsOverlay)) return
    displayedRoute.value = target
  },
  { immediate: true },
)

// Back-compat: ?settings=notifications deep links now redirect to the canonical
// settings URL.
watch(
  () => [route.query.settings, session.isLoggedIn, users.isFinished],
  async ([settings]) => {
    if (settings !== 'notifications' || !session.isLoggedIn || !users.isFinished) return

    await nextTick()
    router.replace({ name: 'SettingsTab', params: { tab: 'notifications' } })
  },
  { immediate: true },
)
</script>
