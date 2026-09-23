<template>
  <!-- A settings tab as a real page. Phones reach a tab from the More menu and each
       one gets this shell: the app's standard mobile header plus the very same panel
       component the desktop dialog mounts (components/Settings/tabs.ts).
       Renders nothing on desktop, the way the RouteGuard it replaced did: the dialog
       holds the panel there, and App.vue points <router-view> at the page the dialog
       is layered over. That swap is async on a cold load, so until it lands this route
       is still what the view renders — a panel mounted here would be a second live
       copy of the dialog's, then vanish when the swap completes. -->
  <template v-if="isPhone">
    <!-- A panel that needs the header for itself draws its own and sets the flag, so
         the two never both render (Communities does this with a community open). -->
    <PageHeaderMobile v-if="!panelOwnsPageHeader" :title="tab?.label ?? 'Settings'">
      <template #prefix>
        <PageHeaderBackButton :to="{ name: 'More' }" />
      </template>
    </PageHeaderMobile>

    <component v-if="tab" :is="tab.component" />
  </template>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PageHeaderMobile, PageHeaderBackButton } from 'frappe-ui'
import { usersReady } from '@/data/users'
import { useIsMobile } from '@/utils/useIsMobile'
import { panelOwnsPageHeader } from '@/components/Settings'
import { useSettingsTabs } from '@/components/Settings/tabs'

const route = useRoute()
const router = useRouter()
const tabs = useSettingsTabs()
const isPhone = useIsMobile()

const routeSlug = computed(() => {
  // The community detail routes (/settings/communities/:communityId/...) still
  // belong to the Communities tab, so they render its panel.
  if (route.name === 'SettingsCommunity') return 'communities'
  return Array.isArray(route.params.tab) ? route.params.tab[0] : route.params.tab
})

const tab = computed(() => tabs.value.find((tab) => tab.slug === routeSlug.value) ?? null)

// Bare /settings, an unknown slug, or a tab this user can't open: fall back to the
// first available tab.
//
// Gated on usersReady, which is what makes a deep link to an admin tab survive a cold
// load. The admin-only tabs are missing from the list until the users resource settles,
// and the non-admin ones are there from the start, so "no match yet" is indistinguishable
// from "not allowed" until the role is known — replacing the URL then would lose the
// requested tab before it could ever match. The desktop dialog gets this for free:
// App.vue only mounts it once usersReady is true — and does this redirect itself, so
// leave it alone there rather than have both push the same replacement.
watch(
  [tab, tabs, usersReady, isPhone],
  () => {
    if (!isPhone.value || !usersReady.value || tab.value || !tabs.value.length) return
    router.replace({ name: 'SettingsTab', params: { tab: tabs.value[0].slug } })
  },
  { immediate: true },
)
</script>
