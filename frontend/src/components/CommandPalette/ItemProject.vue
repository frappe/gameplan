<template>
  <div
    class="flex w-full items-center rounded px-2 py-2 text-base"
    :class="{ 'bg-gray-200': active }"
  >
    <span class="font-medium text-gray-800"> {{ item.title }}&nbsp; </span>
    <span v-if="item.team" class="inline-flex space-x-1 text-gray-600">
      <span>in</span>
      <span> {{ item.team }} </span>
    </span>
    <span class="ml-auto text-gray-600">
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
