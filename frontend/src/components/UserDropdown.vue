<template>
  <Dropdown :options="dropdownItems">
    <template v-slot="{ open }">
      <slot name="trigger" :open="open"></slot>
    </template>
  </Dropdown>
</template>
<script setup>
import { h, computed } from 'vue'
import { Dropdown } from 'frappe-ui'
import { settingsShortcutLabel, showSettingsDialog } from '@/components/Settings'
import { useUser } from '@/data/users'
import { session } from '@/data/session'
import { useTheme } from '@/utils/useTheme'

const user = useUser()
const { currentTheme, setTheme } = useTheme()

const dropdownItems = computed(() => [
  {
    icon: 'lucide-user',
    label: 'My Profile',
    route: {
      name: 'PersonProfileProfile',
      params: { personId: user.user_profile },
    },
  },
  {
    icon: 'lucide-bookmark',
    label: 'Bookmarks',
    route: { name: 'Bookmarks' },
  },
  {
    icon: 'lucide-list-todo',
    label: 'Tasks',
    route: { name: 'MyTasks' },
  },
  {
    icon: 'lucide-files',
    label: 'Pages',
    route: { name: 'MyPages' },
  },
  {
    icon: 'lucide-settings',
    label: 'Settings',
    onClick: () => showSettingsDialog(),
    slots: {
      suffix: () => h('span', { class: 'text-xs text-ink-gray-4' }, settingsShortcutLabel),
    },
  },
  {
    icon: 'lucide-moon',
    label: 'Toggle theme',
    submenu: [
      {
        label: 'Light Mode',
        icon: 'lucide-sun',
        slots: {
          suffix: () => themeCheckmark('light'),
        },
        onClick: () => setTheme('light'),
      },
      {
        label: 'Dark Mode',
        icon: 'lucide-moon',
        slots: {
          suffix: () => themeCheckmark('dark'),
        },
        onClick: () => setTheme('dark'),
      },
      {
        label: 'System Default',
        icon: 'lucide-monitor',
        slots: {
          suffix: () => themeCheckmark('system'),
        },
        onClick: () => setTheme('system'),
      },
    ],
  },
  {
    icon: () => h('span', { class: 'lucide-credit-card' }),
    label: 'Subscription',
    condition: () => user.isNotGuest && window.frappecloud_host && window.site_name,
    onClick: () => {
      window.open(`${window.frappecloud_host}/dashboard/subscription/${window.site_name}`, '_blank')
    },
  },
  {
    icon: 'lucide-log-out',
    label: 'Log out',
    onClick: () => session.logout.submit(),
  },
])

function themeCheckmark(theme) {
  if (currentTheme.value !== theme) return null
  return h('span', { class: 'lucide-check size-4 text-ink-gray-6' })
}
</script>
