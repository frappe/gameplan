import { ref, type Component } from 'vue'
import router from '@/router'

type LucideIconString = `lucide-${string}`

export interface Tab {
  label: string
  /** URL slug for this tab, e.g. `users` → /settings/users */
  slug: string
  icon: Component | LucideIconString
  component: Component
  group?: string
}

// Global state for the settings dialog. The URL is the source of truth: opening,
// closing, and switching tabs all go through the router (see SettingsDialog.vue),
// and these refs are derived from the active route.
export const show = ref(false)
export const activeTab = ref<Tab | null>(null)

// Path of the page the dialog is layered over, so App.vue can keep rendering it
// behind the overlay while the URL is a /settings/* route. Set by the router guard.
export const settingsBackgroundPath = ref<string | null>(null)

// Lets callers deep-link into the Communities tab, optionally with a specific
// community + view (e.g. a discussion's "Manage spaces" action). The community
// selection lives in the URL, so this is a plain navigation.
export type CommunitiesView = 'spaces' | 'members'

export function showCommunitiesSettings(
  communityId: string | null = null,
  view: CommunitiesView = 'spaces',
) {
  if (communityId) {
    router.push({ name: 'SettingsCommunity', params: { communityId, view } })
  } else {
    router.push({ name: 'SettingsTab', params: { tab: 'communities' } })
  }
}

// Registered tabs (kept in sync by SettingsDialog.vue). Used to map a tab's
// display label to its URL slug for the imperative open helper below.
export const tabs: Tab[] = []

export function registerTabs(tabsArray: Tab[]) {
  tabs.splice(0, tabs.length, ...tabsArray)
}

/**
 * Label for the Cmd/Ctrl+Shift+, shortcut that toggles the dialog (handled in
 * SettingsDialog.vue). Shared so every menu entry shows the same hint.
 */
export const settingsShortcutLabel = /Mac/i.test(navigator.platform) ? '⌘⇧,' : 'Ctrl ⇧ ,'

/**
 * Open the settings dialog at a tab, addressed by its display label. Kept for
 * back-compat with existing callers (e.g. `showSettingsDialog('Notifications')`).
 * Navigates to the tab's URL; SettingsDialog.vue reacts to the route change.
 */
export function showSettingsDialog(defaultTab: string | null = null) {
  const slug = slugForLabel(defaultTab) ?? tabs[0]?.slug ?? 'profile'
  router.push({ name: 'SettingsTab', params: { tab: slug } })
}

function slugForLabel(label: string | null): string | null {
  if (!label) return null
  return tabs.find((tab) => tab.label === label)?.slug ?? label.toLowerCase()
}
