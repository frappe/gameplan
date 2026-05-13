<template>
  <Dialog v-model:open="show" size="sm" bare>
    <div class="p-4 pt-5">
      <div class="flex justify-center">
        <div class="flex flex-col items-center">
          <GameplanLogo class="mb-3 size-12" />
          <h3 class="font-semibold text-xl text-ink-gray-9">Gameplan</h3>
          <div class="flex items-center mt-1">
            <div class="text-base text-ink-gray-6">
              {{ appVersion.branch != 'main' ? appVersion.branch : '' }}
              <template v-if="appVersion.branch != 'main'"> ({{ appVersion.commit }}) </template>
              <template v-else>{{ appVersion.tag }}</template>
            </div>

            <Tooltip
              :text="`${appVersion.commit_message} - ${appVersion.commit_date}`"
              placement="top"
            >
              <span class="lucide-info size-3.5 text-ink-gray-8 ml-1" />
            </Tooltip>
          </div>
        </div>
      </div>
      <hr class="border-t my-3 mx-2" />
      <div>
        <a
          v-for="link in links"
          :key="link.label"
          class="flex py-2 px-2 hover:bg-surface-gray-1 rounded cursor-pointer"
          target="_blank"
          :href="link.url"
        >
          <span v-if="link.icon" :class="[link.icon, 'size-4 mr-2 text-ink-gray-7']" />
          <span class="text-base text-ink-gray-8">
            {{ link.label }}
          </span>
        </a>
      </div>
      <hr class="border-t my-3 mx-2" />
      <p class="text-sm text-ink-gray-6 px-2 mt-2">
        © Frappe Technologies Pvt. Ltd. and contributors
      </p>
    </div>
  </Dialog>
</template>
<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import GameplanLogo from './GameplanLogo.vue'
let show = defineModel<boolean>()

let links = [
  {
    label: 'Website',
    url: 'https://frappe.io/gameplan',
    icon: 'lucide-globe',
  },
  {
    label: 'GitHub Repository',
    url: 'https://github.com/frappe/gameplan',
    icon: 'lucide-github',
  },
  {
    label: 'Report an Issue',
    url: 'https://github.com/frappe/gameplan/issues',
    icon: 'lucide-bug',
  },
  {
    label: 'Contact Support',
    url: 'https://support.frappe.io',
    icon: 'lucide-headset',
  },
]

interface AppVersion {
  branch: string
  commit: string
  commit_date: string
  commit_message: string
  tag?: string
}
let appVersion: AppVersion = window.app_version
</script>
