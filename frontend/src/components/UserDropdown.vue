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
        <LucideChevronDown class="ml-auto hidden h-4 w-4 sm:inline text-ink-gray-7" />
      </button>
      <AboutDialog v-model="showAboutDialog" />
    </template>
  </Dropdown>
</template>
<script setup>
import { h, computed, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings'
import GameplanLogo from './GameplanLogo.vue'
import AboutDialog from './AboutDialog.vue'
import { useUser } from '@/data/users'
import { session } from '@/data/session'
import { clear as clearIndexDb } from 'idb-keyval'
import { useTheme } from '@/utils/useTheme'

import LucideCreditCard from '~icons/lucide/credit-card'
import LucideMoon from '~icons/lucide/moon'
import LucideListRestart from '~icons/lucide/list-restart'
import LucideInfo from '~icons/lucide/info'

const user = useUser()
const showAboutDialog = ref(false)
const { setTheme } = useTheme()

const dropdownItems = computed(() => [
  {
    icon: 'user',
    label: 'My Profile',
    route: {
      name: 'PersonProfile',
      params: { personId: user.user_profile },
    },
  },
  {
    icon: 'settings',
    label: 'Settings & Members',
    onClick: () => showSettingsDialog(),
    condition: () => user.isNotGuest,
  },
  {
    icon: LucideMoon,
    label: 'Toggle theme',
    submenu: [
      {
        label: 'Light Mode',
        icon: 'sun',
        onClick: () => setTheme('light'),
      },
      {
        label: 'Dark Mode',
        icon: 'moon',
        onClick: () => setTheme('dark'),
      },
      {
        label: 'System Default',
        icon: 'monitor',
        onClick: () => setTheme('system'),
      },
    ],
  },
  {
    icon: LucideListRestart,
    label: 'Clear cache',
    onClick: clearCache,
  },
  {
    icon: LucideInfo,
    label: 'About',
    onClick: () => {
      showAboutDialog.value = true
    },
  },
  {
    icon: () => h(LucideCreditCard),
    label: 'Subscription',
    condition: () => user.isNotGuest && window.frappecloud_host && window.site_name,
    onClick: () => {
      window.open(`${window.frappecloud_host}/dashboard/subscription/${window.site_name}`, '_blank')
    },
  },
  {
    icon: 'log-out',
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
