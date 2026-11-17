import { computed, defineAsyncComponent, markRaw, type Component } from 'vue'
import { isGameplanAdmin, useSessionUser } from '@/data/users'
import type { Tab } from './index'

// Each tab's screen downloads when the tab first opens. They are large (the emoji
// picker alone carries the whole emoji list), and every page load used to pay for them.
function lazyTab(load: () => Promise<Component>) {
  return markRaw(defineAsyncComponent(load))
}

const ProfileSettings = lazyTab(() => import('./ProfileSettings.vue'))
const PreferencesSettings = lazyTab(() => import('./PreferencesSettings.vue'))
const NotificationsSettings = lazyTab(() => import('./NotificationsSettings.vue'))
const CommunitiesSettings = lazyTab(() => import('./CommunitiesSettings.vue'))
const CustomEmojiSettings = lazyTab(() => import('./CustomEmojiSettings.vue'))
const MembersSettings = lazyTab(() => import('./MembersSettings.vue'))

export interface SettingsTab extends Tab {
  // Tabs that drive global role management / invites; these only make sense for
  // global admins, whose actions the server (require_admin) actually accepts.
  adminOnly?: boolean
  condition?: () => boolean
  prefix?: 'session-avatar'
}

// One definition for both shells: the dialog (desktop, SettingsDialog.vue) and the
// page (phones, pages/SettingsPage.vue) read the same list, so a tab's slug, label
// and gating can't drift between them.
const allTabs: SettingsTab[] = [
  {
    label: 'Profile',
    slug: 'profile',
    group: 'User settings',
    icon: 'lucide-user',
    prefix: 'session-avatar',
    component: ProfileSettings,
  },
  {
    label: 'Preferences',
    slug: 'preferences',
    group: 'User settings',
    icon: 'lucide-sliders-horizontal',
    component: PreferencesSettings,
  },
  {
    label: 'Notifications',
    slug: 'notifications',
    group: 'User settings',
    icon: 'lucide-bell',
    component: NotificationsSettings,
  },
  {
    label: 'Communities',
    slug: 'communities',
    group: 'App settings',
    icon: 'lucide-building-2',
    component: CommunitiesSettings,
    // Every member browses communities here to join or leave one; the management
    // actions inside the tab stay gated per community.
    condition: () => !useSessionUser().isGuest,
  },
  {
    label: 'Emojis',
    slug: 'emojis',
    group: 'App settings',
    icon: 'lucide-smile-plus',
    component: CustomEmojiSettings,
    adminOnly: true,
  },
  {
    label: 'Users',
    slug: 'users',
    group: 'Administration',
    icon: 'lucide-users',
    component: MembersSettings,
    adminOnly: true,
  },
]

/**
 * The tabs this user may open. Admin status loads asynchronously (the users
 * resource is `immediate: false`), so this stays reactive and the list grows once
 * the session user's role resolves.
 */
export function useSettingsTabs() {
  return computed(() =>
    allTabs.filter(
      (tab) => (!tab.adminOnly || isGameplanAdmin()) && (!tab.condition || tab.condition()),
    ),
  )
}
