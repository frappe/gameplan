<template>
  <div class="flex w-full min-w-0 items-center rounded-4 px-2 py-2 text-base" v-if="space">
    <SpaceIcon :icon="space.icon" class="me-3 size-4 shrink-0 text-ink-gray-6" />
    <span
      v-if="community && !item.hideCommunity"
      class="inline-flex min-w-0 shrink font-medium text-ink-gray-5"
    >
      <span class="truncate">
        {{ community?.title }}
      </span>
      <span class="mx-1 grid h-4 shrink-0 place-content-center">
        <span class="lucide-chevron-right size-3 text-ink-gray-5" />
      </span>
    </span>
    <span class="min-w-0 flex-1 truncate font-medium text-ink-gray-7">
      {{ item.title }}&nbsp;
    </span>
    <span class="lucide-lock ms-0.5 size-3 shrink-0 text-ink-gray-6" v-if="space.is_private" />
  </div>
</template>
<script setup lang="ts">
import { useSpace } from '@/data/spaces'
import { useCommunity } from '@/data/communities'
import SpaceIcon from '@/components/SpaceIcon.vue'
import type { CommandPaletteItem } from './registry'

const props = defineProps<{
  item: CommandPaletteItem
}>()

const space = useSpace(() => props.item.name)
const community = useCommunity(() => space.value?.team)
</script>
