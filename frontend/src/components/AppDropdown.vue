<template>
  <!-- The logo is the app menu's trigger. It carries no tooltip and its own
       open/hover treatment (surface-base fill / opacity dim), so it stays a
       bespoke button rather than a RailItem. -->
  <Dropdown :options="dropdownItems" side="bottom" align="start">
    <template #default="{ open }">
      <button
        type="button"
        class="flex size-7 items-center justify-center rounded-[7px] transition focus-visible:ring-0 focus-visible:focus-ring"
        :class="open ? 'bg-surface-base shadow-sm' : 'hover:opacity-90'"
        aria-label="Gameplan menu"
      >
        <GameplanLogo class="size-7 rounded-[7px]" />
      </button>
    </template>
  </Dropdown>

  <AboutDialog v-model="showAboutDialog" />
</template>

<script setup lang="ts">
import { h, markRaw, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import { clear as clearIndexDb } from 'idb-keyval'
import { showSettingsDialog } from '@/components/Settings'
import AboutDialog from './AboutDialog.vue'
import AppSelector from './AppSelector.vue'
import GameplanLogo from './GameplanLogo.vue'
import { openCustomizeSidebarDialog } from './AppRail/customizeSidebar'

const showAboutDialog = ref(false)

// Mirror the Cmd/Ctrl+Shift+, handler in SettingsDialog.vue.
const isMac = /Mac/i.test(navigator.platform)
const settingsShortcut = isMac ? '⌘⇧,' : 'Ctrl ⇧ ,'

const dropdownItems = [
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
    label: 'Settings',
    onClick: () => showSettingsDialog(),
    slots: {
      suffix: () => h('span', { class: 'text-xs text-ink-gray-4' }, settingsShortcut),
    },
  },
  {
    icon: 'lucide-settings-2',
    label: 'Customize sidebar',
    onClick: openCustomizeSidebarDialog,
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
]

function clearCache() {
  localStorage.clear()
  sessionStorage.clear()
  clearIndexDb().then(() => {
    console.log('Cache cleared')
    window.location.reload()
  })
}
</script>
