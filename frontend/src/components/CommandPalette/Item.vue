<template>
  <div
    class="flex w-full min-w-0 items-center rounded-4 px-2 py-2 text-base-medium text-ink-gray-7"
  >
    <span
      v-if="typeof item.icon === 'string'"
      :class="[item.icon, 'me-3 h-4 w-4 shrink-0 text-ink-gray-6']"
    />
    <component
      v-else-if="item.icon"
      :is="item.icon"
      class="me-3 h-4 w-4 shrink-0 text-ink-gray-6"
    />
    <span
      class="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap"
      v-html="item.title"
    />
    <span v-if="item.modified" class="ms-auto shrink-0 whitespace-nowrap ps-2 text-ink-gray-5">
      {{ dayjsLocal(item.modified).fromNow(true) }}
    </span>
    <span v-else-if="item.suffix" class="ms-auto shrink-0 whitespace-nowrap ps-2 text-ink-gray-5">
      {{ item.suffix }}
    </span>
  </div>
</template>
<script setup lang="ts">
import { dayjsLocal } from 'frappe-ui'
import type { CommandPaletteItem } from './registry'

defineProps<{
  item: CommandPaletteItem
}>()
</script>
