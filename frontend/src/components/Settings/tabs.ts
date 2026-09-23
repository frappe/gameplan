import { computed, markRaw } from 'vue'
import { isGameplanAdmin, useSessionUser } from '@/data/users'
import type { Tab } from './index'
import MembersSettings from './MembersSettings.vue'
import CommunitiesSettings from './CommunitiesSettings.vue'
import NotificationsSettings from './NotificationsSettings.vue'
import ProfileSettings from './ProfileSettings.vue'
import CustomEmojiSettings from './CustomEmojiSettings.vue'
import PreferencesSettings from './PreferencesSettings.vue'

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
    condition: () => !useSessionUser().isGuest,
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
