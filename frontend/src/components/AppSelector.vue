<template>
  <div class="text-base text-ink-gray-7">
    <a
      v-for="app in installedApps.data"
      :key="app.name"
      :href="app.route"
      class="flex items-center gap-2 rounded p-1.5 hover:bg-surface-gray-2"
    >
      <img class="h-6 w-6" :src="app.logo" :alt="app.title" />
      <span class="w-full truncate">
        {{ app.title }}
      </span>
    </a>
  </div>
</template>
<script setup>
import { installedApps } from '@/data/apps'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
})
</script>
