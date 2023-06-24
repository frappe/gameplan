<template>
  <Dialog v-model="show" :options="{ size: '5xl' }">
    <template #body>
      <div class="flex" :style="{ height: 'calc(100vh - 8rem)' }">
        <div class="flex w-52 shrink-0 flex-col bg-gray-50 p-2">
          <h1 class="px-2 pt-2 text-lg font-semibold">Settings</h1>
          <div class="mt-3">
            <button
              class="flex h-7 w-full items-center gap-2 rounded px-2 py-1"
              :class="[
                activeTab?.label == tab.label
                  ? 'bg-white shadow-sm'
                  : 'hover:bg-gray-100',
              ]"
              v-for="tab in tabs"
              :key="tab.label"
              @click="activeTab = tab"
            >
              <component :is="tab.icon" class="h-4 w-4 text-gray-700" />
              <span class="text-base text-gray-800">
                {{ tab.label }}
              </span>
            </button>
          </div>
        </div>
        <div class="flex flex-1 flex-col px-16 pt-10">
          <component v-if="activeTab" :is="activeTab.component" />
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script>
import { markRaw } from 'vue'
import { Dialog } from 'frappe-ui'
import Members from './Members.vue'
import ArchivedTeams from './ArchivedTeams.vue'
import LucideUsers from '~icons/lucide/users'
import LucideFolderMinus from '~icons/lucide/folder-minus'

let tabs = [
  {
    label: 'Members',
    icon: LucideUsers,
    component: markRaw(Members),
  },
  {
    label: 'Archive',
    icon: LucideFolderMinus,
    component: markRaw(ArchivedTeams),
  },
]

export default {
  name: 'SettingsDialog',
  props: ['modelValue', 'tab'],
  emits: ['update:modelValue'],
  components: {
    Dialog,
  },
  data() {
    return {
      activeTab: null,
    }
  },
  mounted() {
    if (this.tab) {
      this.activeTab = tabs.find((tab) => tab.label == this.tab)
    } else {
      this.activeTab = tabs[0]
    }
  },
  setup() {
    return { tabs }
  },
  computed: {
    show: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      },
    },
  },
}
</script>
