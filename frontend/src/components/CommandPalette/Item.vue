<template>
  <div
    class="flex w-full min-w-0 items-center rounded px-2 py-2 text-base font-medium text-ink-gray-7"
  >
    <component :is="item.icon" v-if="item.icon" class="mr-3 h-4 w-4 text-ink-gray-6" />
    <span class="overflow-hidden text-ellipsis whitespace-nowrap" v-html="item.title"> </span>
    <span v-if="item.modified" class="ml-auto whitespace-nowrap pl-2 text-ink-gray-5">
      {{ dayjsLocal(item.modified).fromNow(true) }}
    </span>
  </div>
</template>
<script setup>
import { dayjsLocal } from 'frappe-ui'

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
})
</script>
