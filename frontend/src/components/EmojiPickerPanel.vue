<template>
  <!--
    The sticky group headings must hide the emoji scrolling under them, so they
    take their background from whatever surface the panel is dropped on: a
    popover panel here, the bottom sheet there. `bg-inherit` walks that up the
    chain, so every container between here and that surface needs it too.
  -->
  <div class="flex min-h-0 flex-col bg-inherit">
    <div class="flex gap-2 px-2.5 pb-1 pt-2.5">
      <div class="flex-1">
        <FormControl v-model="search" type="text" placeholder="Search by keyword" :debounce="300" />
      </div>
      <slot name="actions" />
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto bg-inherit pb-2.5">
      <div v-if="filteredCustomEmojis.length">
        <div class="sticky top-0 z-10 bg-inherit px-2.5 pb-2 pt-3 text-sm text-ink-gray-6">
          Custom
        </div>
        <div class="grid grid-cols-[repeat(auto-fill,minmax(2rem,1fr))] place-items-center px-2.5">
          <button
            v-for="custom in filteredCustomEmojis"
            :key="custom.name"
            type="button"
            class="flex h-8 w-8 items-center justify-center rounded-md p-1 hover:bg-surface-gray-2 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
            :title="custom.title"
            @click="select(custom.image)"
          >
            <img :src="custom.image" :alt="custom.title" class="size-6 object-contain" />
          </button>
        </div>
      </div>
      <div v-for="(emojis, group) in emojiGroups" :key="group">
        <div class="sticky top-0 z-10 bg-inherit px-2.5 pb-2 pt-3 text-sm text-ink-gray-6">
          {{ group }}
        </div>
        <div class="grid grid-cols-[repeat(auto-fill,minmax(2rem,1fr))] place-items-center px-2.5">
          <button
            v-for="emoji in emojis"
            :key="emoji.description"
            type="button"
            class="h-8 w-8 rounded-md p-1 font-[emoji] text-4xl hover:bg-surface-gray-2 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
            :title="emoji.description"
            @click="select(emoji.emoji)"
          >
            {{ emoji.emoji }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { FormControl } from 'frappe-ui'
import { gemoji } from 'gemoji'
import { customEmojis } from '@/data/customEmojis'

/**
 * The searchable full emoji list, with the workspace's custom emoji on top.
 * Layout-agnostic on purpose: it fills whatever box the parent sizes it to, so
 * the same panel works inside a popover, a hover card and a bottom sheet.
 */

const emit = defineEmits<{
  select: [value: string]
}>()

const search = ref('')

const filteredCustomEmojis = computed(() => {
  const list = customEmojis.data || []
  const query = search.value.toLowerCase().trim()
  if (!query) return list
  return list.filter((emoji) => {
    const haystack = `${emoji.title} ${emoji.keywords || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

const emojiGroups = computed(() => {
  const groups: Record<string, typeof gemoji> = {}
  const query = search.value.toLowerCase()

  for (const emoji of gemoji) {
    if (query) {
      const keywords = [emoji.description, ...emoji.names, ...emoji.tags].join(' ').toLowerCase()
      if (!keywords.includes(query)) continue
    }

    groups[emoji.category] ??= []
    groups[emoji.category].push(emoji)
  }

  if (!Object.keys(groups).length) groups['No results'] = []
  return groups
})

function select(value: string) {
  emit('select', value)
}
</script>
