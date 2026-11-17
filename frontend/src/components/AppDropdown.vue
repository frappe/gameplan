<template>
  <!-- The logo is the app menu's trigger. It carries no tooltip and its own
       open/hover treatment (surface-base fill / opacity dim), so it stays a
       bespoke button rather than a SidebarRailItem. -->
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
import { computed, h, ref } from 'vue'
import { Dropdown } from 'frappe-ui'
import { clear as clearIndexDb } from 'idb-keyval'
import { settingsShortcutLabel, showSettingsDialog } from '@/components/Settings'
import AboutDialog from './AboutDialog.vue'
import GameplanLogo from './GameplanLogo.vue'
import { openCustomizeSidebarDialog } from './AppRail/customizeSidebar'
import { installedApps } from '@/data/apps'

const showAboutDialog = ref(false)

// One normal menu item per app (not a single custom row holding every link):
// frappe-ui's `slots.item` rows remount on each re-render, which drops the
// focus reka-ui just gave them and closes the submenu.
// Menu icons only accept `lucide-*` / emoji strings or a component, so the
// app logo URL is wrapped in a minimal <img> component. It inherits the size
// and colour classes frappe-ui passes to icon components.
function appIcon(logo: string) {
  return () => h('img', { src: logo, alt: '', class: 'rounded-sm object-contain' })
}

// `route` would go through vue-router (base /g); app routes are other pages
// (/app, /raven, ...), so navigate with a full page load instead.
const appItems = computed(() =>
  (installedApps.data ?? []).map((app) => ({
    label: app.title,
    icon: appIcon(app.logo),
    onClick: () => {
      window.location.href = app.route
    },
  })),
)

const dropdownItems = computed(() => [
  {
    icon: 'lucide-layout-grid',
    label: 'Apps',
    submenu: appItems.value,
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
