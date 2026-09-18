<template>
  <SettingsDialog
    v-model:open="show"
    v-model:tab="activeTabValue"
    size="5xl"
    :shortcut="false"
    :unmount-on-hide="false"
  >
    <SettingsSidebar class="gp-settings-sidebar">
      <!-- Phones get the dialog full-screen with no backdrop to tap and no Esc
           key, so they need an explicit way out. -->
      <div class="flex items-center justify-between sm:hidden">
        <h2 class="px-2 text-lg-semibold text-ink-gray-8">Settings</h2>
        <Button variant="ghost" icon="lucide-x" aria-label="Close settings" @click="show = false" />
      </div>
      <div class="gp-settings-nav space-y-4 !mt-2 sm:!mt-0">
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
      </div>
    </SettingsSidebar>
    <SettingsContent class="gp-settings-content">
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
import { computed, markRaw, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventListener } from '@vueuse/core'
import {
  Button,
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
    // Every member browses communities here to join or leave one; the management
    // actions inside the tab stay gated per community.
    condition: () => !sessionUser.isGuest,
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

// On phones the nav is one horizontally scrolling row, so a deep link to a later
// tab (e.g. /settings/communities) would otherwise open with its tab off-screen.
// Only the nav row itself is scrolled, never the page. flush 'post' plus the
// open watch cover the first open, when the tabs mount after the dialog does.
function revealActiveTab() {
  nextTick(() => {
    let nav = document.querySelector<HTMLElement>('.gp-settings-nav')
    let tab = nav?.querySelector<HTMLElement>('[role="tab"][data-state="active"]')
    if (!nav || !tab || nav.scrollWidth <= nav.clientWidth) return
    let navRect = nav.getBoundingClientRect()
    let tabRect = tab.getBoundingClientRect()
    if (tabRect.left < navRect.left || tabRect.right > navRect.right) {
      nav.scrollLeft += tabRect.left - navRect.left - (navRect.width - tabRect.width) / 2
    }
  })
}
watch([() => activeTab.value?.slug, show], revealActiveTab, { flush: 'post' })

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

<style>
/* Phone layout. frappe-ui's SettingsDialog sizes itself full-screen below `sm`
   but still sits inside the Dialog's padded, rounded card, stacks the whole
   vertical nav above the content (up to 38vh), and keeps the desktop 4.4rem
   panel gutters, leaving a narrow strip for the actual settings. Drop the card
   chrome, turn the nav into a single scrollable row of tabs, and use phone
   gutters in every panel.
   Workaround: this belongs in frappe-ui's SettingsDialog; drop it once the
   library handles phones itself (upstream PR: TODO). */
@media (max-width: 639.98px) {
  .dialog-scroll-container:has(.gp-settings-content) > div {
    padding: 0;
  }

  .dialog-content:has(.gp-settings-content) {
    margin: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .gp-settings-sidebar {
    max-height: none;
    padding: 0.5rem 0.75rem;
  }

  .gp-settings-nav {
    display: flex;
    gap: 0.25rem;
    margin-inline: -0.75rem;
    padding-inline: 0.75rem;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .gp-settings-nav::-webkit-scrollbar {
    display: none;
  }

  .gp-settings-nav > * {
    display: flex;
    flex-shrink: 0;
    margin-top: 0 !important;
  }

  /* Group headings don't fit a single row; the tabs alone are enough. */
  .gp-settings-nav > * > :not(:last-child) {
    display: none;
  }

  .gp-settings-nav > * > :last-child {
    flex-direction: row;
    gap: 0.25rem;
  }

  .gp-settings-nav [role='tab'] {
    width: auto;
    flex-shrink: 0;
  }

  .gp-settings-content [role='tabpanel'] > :not([data-slot='scroll-area']) {
    padding: 1.25rem 1rem 0;
  }

  .gp-settings-content
    [role='tabpanel']
    > [data-slot='scroll-area']
    > [data-slot='scroll-area-viewport'] {
    padding-inline: 1rem;
    padding-bottom: 2rem;
  }
}
</style>
