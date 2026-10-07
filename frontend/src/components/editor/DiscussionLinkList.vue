<template>
  <div
    v-if="items.length"
    class="relative max-h-[300px] min-w-40 max-w-96 overflow-y-auto rounded-6 border border-outline-gray-2 bg-surface-elevation-2 p-1 text-base shadow-2xl"
  >
    <button
      v-for="(item, index) in items"
      :key="item.name"
      :ref="(el) => setItemRef(el, index)"
      type="button"
      :class="[
        'flex w-full items-center gap-3 whitespace-nowrap rounded-4 px-2 py-1.5 text-sm text-ink-gray-9',
        index === selectedIndex ? 'bg-surface-gray-2' : '',
      ]"
      @click="command(item)"
      @mouseover="selectedIndex = index"
    >
      <span class="truncate">{{ item.title }}</span>
      <span class="ml-auto shrink-0 text-ink-gray-5">{{ getSpace(item.project)?.title }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUpdate, ref, watch } from 'vue'
import { getSpace } from '@/data/spaces'

export interface DiscussionLinkItem {
  name: string
  title: string
  project: string
}

const props = defineProps<{
  items: DiscussionLinkItem[]
  command: (item: DiscussionLinkItem) => void
}>()

const selectedIndex = ref(0)
const itemRefs = ref<HTMLElement[]>([])

watch(
  () => props.items,
  () => {
    selectedIndex.value = 0
  },
)

onBeforeUpdate(() => {
  itemRefs.value = []
})

function setItemRef(el: unknown, index: number) {
  if (el instanceof HTMLElement) itemRefs.value[index] = el
}

function onKeyDown({ event }: { event: KeyboardEvent }) {
  const count = props.items.length
  if (!count) return false

  if (event.key === 'ArrowUp') {
    selectedIndex.value = (selectedIndex.value + count - 1) % count
  } else if (event.key === 'ArrowDown') {
    selectedIndex.value = (selectedIndex.value + 1) % count
  } else if (event.key === 'Enter') {
    props.command(props.items[selectedIndex.value])
    return true
  } else {
    return false
  }

  nextTick(() => itemRefs.value[selectedIndex.value]?.scrollIntoView({ block: 'nearest' }))
  return true
}

defineExpose({ onKeyDown })
</script>
