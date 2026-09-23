<template>
  <!-- A settings tab as a real page. Phones reach a tab from the More menu and each
       one gets this shell: the app's standard mobile header plus the very same panel
       component the desktop dialog mounts (components/Settings/tabs.ts). Desktop
       never renders this — App.vue keeps the dialog over the background page. -->
  <!-- A panel that needs the header for itself draws its own and sets the flag, so
       the two never both render (Communities does this with a community open). -->
  <PageHeaderMobile v-if="!panelOwnsPageHeader" class="sm:hidden" :title="tab?.label ?? 'Settings'">
    <template #prefix>
      <PageHeaderBackButton :to="{ name: 'More' }" />
    </template>
  </PageHeaderMobile>

  <component v-if="tab" :is="tab.component" />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PageHeaderMobile, PageHeaderBackButton } from 'frappe-ui'
import { panelOwnsPageHeader } from '@/components/Settings'
import { useSettingsTabs } from '@/components/Settings/tabs'

const route = useRoute()
const router = useRouter()
const tabs = useSettingsTabs()

const routeSlug = computed(() => {
  // The community detail routes (/settings/communities/:communityId/...) still
  // belong to the Communities tab, so they render its panel.
  if (route.name === 'SettingsCommunity') return 'communities'
  return Array.isArray(route.params.tab) ? route.params.tab[0] : route.params.tab
})

const tab = computed(() => tabs.value.find((tab) => tab.slug === routeSlug.value) ?? null)

// Bare /settings, an unknown slug, or a tab this user can't open: fall back to the
// first available tab once the list is known. Re-runs when admin-only tabs resolve
// async, so a deep link to an admin tab works as soon as permissions load.
watch(
  [tab, tabs],
  () => {
    if (tab.value || !tabs.value.length) return
    router.replace({ name: 'SettingsTab', params: { tab: tabs.value[0].slug } })
  },
  { immediate: true },
)
</script>
