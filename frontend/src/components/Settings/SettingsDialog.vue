<template>
  <Dialog v-model="show" :options="{ size: '4xl' }">
    <template #body>
      <div class="flex" :style="{ height: 'calc(100vh - 8rem)' }">
        <div class="flex w-52 shrink-0 flex-col space-y-1 bg-gray-50 p-2">
          <button
            class="flex items-center gap-2 rounded-lg px-2 py-1"
            :class="[
              activeTab?.label == tab.label
                ? 'bg-gray-200'
                : 'hover:bg-gray-100',
            ]"
            v-for="tab in tabs"
            :key="tab.label"
            @click="activeTab = tab"
          >
            <FeatherIcon :name="tab.icon" class="h-4 w-4 text-gray-600" />
            <span class="text-base text-gray-900">
              {{ tab.label }}
            </span>
          </button>
        </div>
        <div class="flex flex-1 flex-col">
          <component v-if="activeTab" :is="activeTab.component" />
        </div>
      </div>
    </template>
  </Dialog>
</template>
<script>
import { markRaw } from 'vue'
import { Dialog, FeatherIcon } from 'frappe-ui'
import Members from './Members.vue'
import ArchivedTeams from './ArchivedTeams.vue'

let tabs = [
  {
    label: 'Members',
    icon: 'users',
    component: markRaw(Members),
  },
  {
    label: 'Archived Teams',
    icon: 'folder-minus',
    component: markRaw(ArchivedTeams),
  },
]

export default {
  name: 'SettingsDialog',
  props: ['modelValue', 'tab'],
  emits: ['update:modelValue'],
  components: {
    Dialog,
    FeatherIcon,
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
