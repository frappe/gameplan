<template>
  <SettingsDialog
    v-model="show"
    v-model:tab="activeTabValue"
    size="5xl"
    :shortcut="false"
    :unmount-on-hide="false"
  >
    <SettingsSidebar>
      <SettingsNavGroup v-for="group in tabGroups" :key="group.label" :label="group.label">
        <SettingsNavItem v-for="tab in group.tabs" :key="tab.label" :value="tab.slug">
          <template #prefix>
            <UserAvatar
              v-if="tab.prefix === 'session-avatar'"
              :user="sessionUser.name"
              size="xs"
              class="shrink-0"
            />
            <span v-else :class="[tab.icon, 'size-4 shrink-0 text-ink-gray-6']" />
          </template>
          {{ tab.label }}
        </SettingsNavItem>
      </SettingsNavGroup>
    </SettingsSidebar>
    <SettingsContent class="settings-dialog-content">
      <!-- One reka-ui tabpanel per tab. unmount-on-hide=false keeps a visited
           panel mounted (just hidden) so switching back is instant and inactive
           tabs keep reacting to shared state (e.g. the active route); the v-if
           defers first mount until a tab is opened, so the heavy Users and
           Communities trees stay lazy. -->
      <SettingsPanel v-for="tab in tabs" :key="tab.slug" :value="tab.slug">
        <component
          v-if="visitedTabs.has(tab.slug)"
          :is="tab.component"
          @close-dialog="show = false"
        />
      </SettingsPanel>
    </SettingsContent>
  </SettingsDialog>
</template>

<script setup lang="ts">
import { computed, markRaw, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventListener } from '@vueuse/core'
import {
  SettingsDialog,
  SettingsSidebar,
  SettingsNavGroup,
  SettingsNavItem,
  SettingsContent,
  SettingsPanel,
} from 'frappe-ui'
import { show, activeTab, registerTabs, settingsBackgroundPath, type Tab } from './index'
import { getHomeRoute } from '@/router'
import UserAvatar from '@/components/UserAvatar.vue'
import { isGameplanAdmin, useSessionUser } from '@/data/users'
import { useCanManageCommunities } from '@/composables/useCanManageCommunities'
import MembersSettings from './MembersSettings.vue'
import CommunitiesSettings from './CommunitiesSettings.vue'
import NotificationsSettings from './NotificationsSettings.vue'
import ProfileSettings from './ProfileSettings.vue'
import CustomEmojiSettings from './CustomEmojiSettings.vue'
import PreferencesSettings from './PreferencesSettings.vue'

interface SettingsTab extends Tab {
  // Tabs that drive global role management / invites; these only make sense for
  // global admins, whose actions the server (require_admin) actually accepts.
  adminOnly?: boolean
  condition?: () => boolean
  prefix?: 'session-avatar'
}

const route = useRoute()
const router = useRouter()

interface TabGroup {
  label: string
  tabs: SettingsTab[]
}

const canManageCommunities = useCanManageCommunities()
const sessionUser = useSessionUser()

const allTabs: SettingsTab[] = [
  {
    label: 'Profile',
    slug: 'profile',
    group: 'User settings',
    icon: 'lucide-user',
    prefix: 'session-avatar',
    component: markRaw(ProfileSettings),
  },
  {
    label: 'Preferences',
    slug: 'preferences',
    group: 'User settings',
    icon: 'lucide-sliders-horizontal',
    component: markRaw(PreferencesSettings),
  },
  {
    label: 'Notifications',
    slug: 'notifications',
    group: 'User settings',
    icon: 'lucide-bell',
    component: markRaw(NotificationsSettings),
  },
  {
    label: 'Communities',
    slug: 'communities',
    group: 'App settings',
    icon: 'lucide-building-2',
    component: markRaw(CommunitiesSettings),
    condition: () => canManageCommunities.value,
  },
  {
    label: 'Emojis',
    slug: 'emojis',
    group: 'App settings',
    icon: 'lucide-smile-plus',
    component: markRaw(CustomEmojiSettings),
    adminOnly: true,
  },
  {
    label: 'Users',
    slug: 'users',
    group: 'Administration',
    icon: 'lucide-users',
    component: markRaw(MembersSettings),
    adminOnly: true,
  },
]

// Admin status loads asynchronously (the users resource is immediate: false), so
// keep this reactive and re-register once the session user's role resolves.
const tabs = computed(() =>
  allTabs.filter(
    (tab) => (!tab.adminOnly || isGameplanAdmin()) && (!tab.condition || tab.condition()),
  ),
)
const tabGroups = computed<TabGroup[]>(() => {
  let groups: TabGroup[] = []

  for (let tab of tabs.value) {
    let label = tab.group || 'Settings'
    let group = groups.find((group) => group.label === label)
    if (!group) {
      group = { label, tabs: [] }
      groups.push(group)
    }
    group.tabs.push(tab)
  }

  return groups
})

// Keep the label→slug registry in sync for the imperative showSettingsDialog().
watch(tabs, (list) => registerTabs(list), { immediate: true })

const onSettingsRoute = computed(() => route.matched.some((r) => r.meta?.settingsOverlay))
const routeTab = computed(() => {
  // The nested community detail routes (/settings/communities/:communityId/...)
  // still belong to the Communities tab, so the dialog highlights and mounts it.
  if (route.name === 'SettingsCommunity') return 'communities'
  return Array.isArray(route.params.tab) ? route.params.tab[0] : route.params.tab
})

// Route → store: the URL drives which tab is shown and whether the dialog is open.
// Re-runs when admin-only tabs resolve async, so a deep link to an admin tab works
// once permissions load.
watch(
  [routeTab, onSettingsRoute, tabs],
  () => {
    if (!onSettingsRoute.value) {
      show.value = false
      return
    }
    const match = tabs.value.find((tab) => tab.slug === routeTab.value)
    if (!match) {
      // Bare /settings, an unknown slug, or a tab the user can't access: fall back
      // to the first available tab once the tab list is known.
      if (tabs.value.length) {
        router.replace({ name: 'SettingsTab', params: { tab: tabs.value[0].slug } })
      }
      return
    }
    activeTab.value = match
    show.value = true
  },
  { immediate: true },
)

// Closing the dialog (Esc, backdrop click, or the X) returns to the underlying page.
watch(show, (open) => {
  if (!open && onSettingsRoute.value) {
    router.push(settingsBackgroundPath.value || getHomeRoute())
  }
})

// Drives reka-ui Tabs (v-model:tab): the value mirrors the active slug, and
// selecting a tab (click or keyboard) pushes the canonical settings URL, which
// the route watcher above resolves back into activeTab.
const activeTabValue = computed<string>({
  get: () => activeTab.value?.slug ?? '',
  set: (slug) => {
    if (slug) router.push({ name: 'SettingsTab', params: { tab: slug } })
  },
})

// Track which tabs have been opened so their panels mount lazily (the heavy
// Users/Communities trees only build on first visit). Combined with the kit's
// :unmount-on-hide="false", a visited panel then stays mounted and cached.
const visitedTabs = ref(new Set<string>())
watch(
  () => activeTab.value?.slug,
  (slug) => {
    if (slug) visitedTabs.value.add(slug)
  },
  { immediate: true },
)

// Route-aware Cmd/Ctrl+Shift+. toggle. The kit's built-in shortcut is disabled
// (:shortcut="false") because the dialog's open state is driven by the URL here.
// Use e.code since Shift rewrites e.key for "." to ">" on most layouts.
useEventListener(window, 'keydown', (e: KeyboardEvent) => {
  if (e.code !== 'Comma' || !e.shiftKey || !(e.metaKey || e.ctrlKey)) return
  e.preventDefault()
  if (onSettingsRoute.value) {
    router.push(settingsBackgroundPath.value || getHomeRoute())
    return
  }
  const slug = activeTab.value?.slug || tabs.value[0]?.slug
  if (slug) router.push({ name: 'SettingsTab', params: { tab: slug } })
})
</script>
