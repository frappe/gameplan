<template>
  <div class="flex w-full items-center rounded px-2 py-2 text-base" v-if="space">
    <span class="font-[emoji] size-4 leading-4 text-lg mr-3">{{ space.icon }}</span>
    <span v-if="category" class="font-medium inline-flex items-end text-ink-gray-5">
      {{ category?.title }}
      <div class="h-4 grid place-content-center mx-1">
        <span class="lucide-chevron-right size-3 text-ink-gray-5" />
      </div>
    </span>
    <span class="font-medium text-ink-gray-7"> {{ item.title }}&nbsp; </span>
    <span class="lucide-lock size-3 text-ink-gray-6 ml-0.5" v-if="space.is_private" />
  </div>
</template>
<script setup lang="ts">
import { useSpace } from '@/data/spaces'
import { useTeam } from '@/data/teams'
const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
})

const space = useSpace(() => props.item.name)
const category = useTeam(() => space.value?.team)
</script>
