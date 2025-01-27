<template>
  <div class="flex w-full items-center rounded px-2 py-2 text-base" v-if="space">
    <span class="font-[emoji] size-4 leading-4 text-lg mr-3">{{ space.icon }}</span>
    <span class="font-medium text-ink-gray-8"> {{ item.title }}&nbsp; </span>
    <LucideLock class="size-3 text-ink-gray-6 ml-0.5" v-if="space.is_private" />
  </div>
</template>
<script setup>
import { useSpace } from '@/data/spaces'
import LucideLock from '~icons/lucide/lock'

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
})

const space = useSpace(() => props.item.name)
</script>
