<template>
  <Dialog v-model="show" :options="{ size: '5xl' }">
    <template #body>
      <div class="flex" :style="{ height: 'calc(100vh - 8rem)' }">
        <div class="flex w-52 shrink-0 flex-col bg-surface-menu-bar p-2">
          <Dialog.Title as-child>
            <h1 class="px-2 pt-2 text-lg font-semibold">Settings</h1>
          </Dialog.Title>
          <div class="mt-3">
            <button
              class="flex h-7 w-full items-center gap-2 rounded px-2 py-1"
              :class="[
                activeTab?.label == tab.label
                  ? 'bg-surface-white shadow-sm'
                  : 'hover:bg-surface-gray-2',
              ]"
              v-for="tab in tabs"
              :key="tab.label"
              @click="activeTab = tab"
            >
              <component :is="tab.icon" class="h-4 w-4 text-ink-gray-6" />
              <span class="text-base text-ink-gray-7">
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

<script setup lang="ts">
import { markRaw, onMounted, type Component } from 'vue'
import { Dialog } from 'frappe-ui'
import { show, activeTab, registerTabs } from './index'
import Members from './Members.vue'
import InvitePeople from './InvitePeople.vue'
import SettingsTabDialog from './SettingsTab.vue'
import LucideUsers from '~icons/lucide/users'
import LucideUsersPlus from '~icons/lucide/user-plus'
import LucideFolderMinus from '~icons/lucide/folder-minus'
import LucideSettings from '~icons/lucide/settings'

interface Tab {
  label: string
  icon: Component
  component: Component
}

const tabs: Tab[] = [
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
    label: 'Settings',
    icon: LucideSettings,
    component: markRaw(SettingsTabDialog),
  },
]

// Register tabs on component mount
onMounted(() => {
  registerTabs(tabs)
})
</script>
