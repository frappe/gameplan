<template>
  <Dropdown :options="dropdownItems">
    <template v-slot="{ open }">
      <button
        class="flex w-[14rem] items-center rounded-md px-2 py-2 text-left"
        :class="open ? 'bg-surface-selected shadow-sm' : 'hover:bg-surface-gray-3'"
      >
        <GameplanLogo class="w-8 h-8 rounded" />
        <div class="ml-2 flex flex-col">
          <div class="text-base font-medium text-ink-gray-8 leading-none">Gameplan</div>
          <div class="mt-1 hidden text-sm text-ink-gray-6 sm:inline leading-none">
            {{ user.full_name }}
          </div>
        </div>
        <span class="lucide-chevron-down ml-auto hidden h-4 w-4 sm:inline text-ink-gray-7" />
      </button>
      <AboutDialog v-model="showAboutDialog" />
    </template>
  </Dropdown>
</template>
<script setup>
import { h, computed, ref, markRaw } from 'vue'
import { Dropdown } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings'
import GameplanLogo from './GameplanLogo.vue'
import AboutDialog from './AboutDialog.vue'
import AppSelector from './AppSelector.vue'
import { useUser } from '@/data/users'
import { session } from '@/data/session'
import { clear as clearIndexDb } from 'idb-keyval'
import { useTheme } from '@/utils/useTheme'

const user = useUser()
const showAboutDialog = ref(false)
const { setTheme } = useTheme()

const dropdownItems = computed(() => [
  {
    icon: 'lucide-user',
    label: 'My Profile',
    route: {
      name: 'PersonProfile',
      params: { personId: user.user_profile },
    },
  },
  {
    icon: 'lucide-layout-grid',
    label: 'Apps',
    submenu: [
      {
        component: markRaw(AppSelector),
      },
    ],
  },
  {
    icon: 'lucide-settings',
    label: 'Settings & Members',
    onClick: () => showSettingsDialog(),
    condition: () => user.isNotGuest,
  },
  {
    icon: 'lucide-moon',
    label: 'Toggle theme',
    submenu: [
      {
        label: 'Light Mode',
        icon: 'lucide-sun',
        onClick: () => setTheme('light'),
      },
      {
        label: 'Dark Mode',
        icon: 'lucide-moon',
        onClick: () => setTheme('dark'),
      },
      {
        label: 'System Default',
        icon: 'lucide-monitor',
        onClick: () => setTheme('system'),
      },
    ],
  },
  {
    icon: 'lucide-list-restart',
    label: 'Clear cache',
    onClick: clearCache,
  },
  {
    icon: 'lucide-info',
    label: 'About',
    onClick: () => {
      showAboutDialog.value = true
    },
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

function clearCache() {
  localStorage.clear()
  sessionStorage.clear()
  clearIndexDb().then(() => {
    console.log('Cache cleared')
    window.location.reload()
  })
}
</script>
