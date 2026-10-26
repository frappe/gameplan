<template>
  <div
    v-if="items.length"
    class="min-w-40 max-w-96 rounded-6 border border-outline-gray-2 bg-surface-elevation-2 p-1 text-base shadow-2xl"
  >
    <div
      v-for="(item, index) in items"
      :key="item.name"
      role="option"
      :aria-selected="index === selectedIndex"
      :class="[
        'group flex w-full cursor-pointer items-center gap-3 whitespace-nowrap rounded-4 px-2 py-1.5 text-sm text-ink-gray-9',
        index === selectedIndex ? 'bg-surface-gray-2' : '',
      ]"
      @click="command(item)"
      @mouseover="selectedIndex = index"
    >
      <span class="truncate">{{ item.title }}</span>
      <span class="relative ml-auto flex shrink-0 items-center justify-end">
        <span class="text-ink-gray-5 transition-opacity group-hover:opacity-0">
          {{ spacePath(item.project) }}
        </span>
        <Button
          size="xs"
          label="Preview"
          class="absolute right-0 opacity-0 group-hover:opacity-100"
          @click.stop="command({ ...item, preview: true })"
        />
      </span>
    </div>
    <div class="mt-1 border-t border-outline-gray-1 px-2 pb-0.5 pt-1.5 text-xs text-ink-gray-5">
      ↵ link · ⇧↵ preview
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import { getSpace } from '@/data/spaces'
import { getCommunity } from '@/data/communities'

export interface DiscussionLinkItem {
  name: string
  title: string
  project: string
  preview?: boolean
}

const props = defineProps<{
  items: DiscussionLinkItem[]
  command: (item: DiscussionLinkItem) => void
}>()

const selectedIndex = ref(0)

watch(
  () => props.items,
  () => {
    selectedIndex.value = 0
  },
)

function spacePath(project: string) {
  const space = getSpace(project)
  const community = space?.team ? getCommunity(space.team) : null
  return [community?.title, space?.title].filter(Boolean).join(' / ')
}

function onKeyDown({ event }: { event: KeyboardEvent }) {
  const count = props.items.length
  if (!count) return false

  if (event.key === 'ArrowUp') {
    selectedIndex.value = (selectedIndex.value + count - 1) % count
  } else if (event.key === 'ArrowDown') {
    selectedIndex.value = (selectedIndex.value + 1) % count
  } else if (event.key === 'Enter') {
    props.command({ ...props.items[selectedIndex.value], preview: event.shiftKey })
  } else {
    return false
  }
  return true
}

defineExpose({ onKeyDown })
</script>
