<template>
  <Dialog v-model="show" :options="{ size: '5xl' }">
    <template #body>
      <div class="flex" :style="{ height: 'calc(100vh - 8rem)' }">
        <div class="flex w-52 shrink-0 flex-col bg-surface-menu-bar p-2">
          <h1 class="px-2 pt-2 text-lg font-semibold">Settings</h1>
          <div class="mt-3">
            <button
              class="flex h-7 w-full items-center gap-2 rounded px-2 py-1"
              :class="[activeTab?.label == tab.label ? 'bg-surface-white shadow-sm' : 'hover:bg-surface-gray-2']"
              v-for="tab in tabs"
              :key="tab.label"
              @click="activeTab = tab"
            >
              <component :is="tab.icon" class="h-4 w-4 text-ink-gray-7" />
              <span class="text-base text-ink-gray-8">
                {{ tab.label }}
              </span>
            </button>
          </div>
        </div>
        <div class="flex flex-1 flex-col px-16 pt-10">
          <component v-if="activeTab" :is="activeTab.component" @close-dialog="show = false" />
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script>
import { markRaw, ref } from 'vue'
import { Dialog } from 'frappe-ui'
import Members from './Members.vue'
import ArchivedTeams from './ArchivedTeams.vue'
import InvitePeople from './InvitePeople.vue'
import SettingsTabDialog from './SettingsTab.vue'
import LucideUsers from '~icons/lucide/users'
import LucideUsersPlus from '~icons/lucide/user-plus'
import LucideFolderMinus from '~icons/lucide/folder-minus'
import LucideSettings from '~icons/lucide/settings'

let tabs = [
  {
    label: 'Members',
    icon: LucideUsers,
    component: markRaw(Members),
  },
  {
    label: 'Invites',
    icon: LucideUsersPlus,
    component: markRaw(InvitePeople),
  },
  {
    label: 'Archive',
    icon: LucideFolderMinus,
    component: markRaw(ArchivedTeams),
  },
  {
    label: 'Settings',
    icon: LucideSettings,
    component: markRaw(SettingsTabDialog),
  },
]

let show = ref(false)
let activeTab = ref(null)

export function showSettingsDialog(defaultTab = null) {
  show.value = true
  if (defaultTab) {
    activeTab.value = tabs.find((tab) => tab.label == defaultTab)
  } else {
    activeTab.value = tabs[0]
  }
}

export default {
  name: 'SettingsDialog',
  components: {
    Dialog,
  },
  setup() {
    return { tabs, show, activeTab }
  },
}
</script>
