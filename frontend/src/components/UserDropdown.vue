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
import { h, computed, onMounted, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings/SettingsDialog.vue'
import GameplanLogo from './GameplanLogo.vue'
import AboutDialog from './AboutDialog.vue'
import { useUser } from '@/data/users'
import { session } from '@/data/session'
import { clear as clearIndexDb } from 'idb-keyval'

import LucideCreditCard from '~icons/lucide/credit-card'
import LucideMoon from '~icons/lucide/moon'
import LucideListRestart from '~icons/lucide/list-restart'
import LucideInfo from '~icons/lucide/info'

const user = useUser()
const showAboutDialog = ref(false)

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
    onClick: toggleTheme,
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

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme')
  let theme = currentTheme === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
}

function clearCache() {
  localStorage.clear()
  sessionStorage.clear()
  clearIndexDb().then(() => {
    console.log('Cache cleared')
    window.location.reload()
  })
}

onMounted(() => {
  const theme = localStorage.getItem('theme')
  if (['light', 'dark'].includes(theme)) {
    document.documentElement.setAttribute('data-theme', theme)
  }
})
</script>
