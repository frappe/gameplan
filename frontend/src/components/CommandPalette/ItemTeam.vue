<template>
  <div
    class="flex w-full items-center rounded px-2 py-2 text-base"
    :class="{ 'bg-surface-gray-3': active }"
  >
    <span class="mr-3 h-4 w-4">{{ item.icon }}</span>
    <span class="font-medium text-ink-gray-8"> {{ item.title }}&nbsp; </span>
    <span class="ml-auto text-ink-gray-5">
      {{ $dayjs(item.modified).fromNow(true) }}
    </span>
  </div>
</template>
<script setup>
const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  active: {
    type: Boolean,
    required: true,
  },
})
</script>
