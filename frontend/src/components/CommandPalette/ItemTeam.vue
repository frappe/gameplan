<template>
  <div class="flex w-full items-center rounded px-2 py-2 text-base">
    <span class="mr-3 h-4 w-4">{{ item.icon }}</span>
    <span class="font-medium text-ink-gray-7"> {{ item.title }}&nbsp; </span>
    <span class="ml-auto text-ink-gray-5">
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
