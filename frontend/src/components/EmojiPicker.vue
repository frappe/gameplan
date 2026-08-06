<template>
  <Popover :side="side" :align="align">
    <template #trigger="triggerProps">
      <slot name="trigger" v-bind="triggerProps">
        <button type="button">
          <span class="text-base">{{ modelValue || '' }}</span>
        </button>
      </slot>
    </template>
    <!-- shell (bg, radius, shadow, ring) is provided by Popover's PopoverPanel -->
    <template #default="{ close }">
      <div class="h-96 w-96 overflow-y-auto pb-2.5">
        <div class="flex gap-2 pb-1 px-2.5 pt-2.5">
          <div class="flex-1">
            <FormControl
              v-model="search"
              type="text"
              placeholder="Search by keyword"
              :debounce="300"
            />
          </div>
          <Button @click="setRandom">Random</Button>
        </div>
        <div v-if="filteredCustomEmojis.length">
          <div
            class="sticky top-0 z-10 px-2.5 bg-surface-elevation-2 pb-2 pt-3 text-sm text-ink-gray-6"
          >
            Custom
          </div>
          <div class="grid grid-cols-12 place-items-center px-2.5">
            <button
              v-for="custom in filteredCustomEmojis"
              :key="custom.name"
              type="button"
              class="flex h-8 w-8 items-center justify-center rounded-md p-1 hover:bg-surface-gray-2 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
              :title="custom.title"
              @click="selectEmoji(custom.image, close)"
            >
              <img :src="custom.image" :alt="custom.title" class="size-6 object-contain" />
            </button>
          </div>
        </div>
        <div v-for="(emojis, group) in emojiGroups" :key="group">
          <div
            class="sticky top-0 z-10 px-2.5 bg-surface-elevation-2 pb-2 pt-3 text-sm text-ink-gray-6"
          >
            {{ group }}
          </div>
          <div class="grid grid-cols-12 place-items-center px-2.5">
            <button
              v-for="emoji in emojis"
              :key="emoji.description"
              type="button"
              class="h-8 w-8 rounded-md p-1 text-4xl hover:bg-surface-gray-2 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
              :title="emoji.description"
              @click="selectEmoji(emoji.emoji, close)"
            >
              {{ emoji.emoji }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </Popover>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button, FormControl, Popover } from 'frappe-ui'
import { gemoji } from 'gemoji'
import { getRandomNumber } from '@/utils'
import { customEmojis } from '@/data/customEmojis'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    setDefault?: boolean
    side?: 'top' | 'right' | 'bottom' | 'left'
    align?: 'start' | 'center' | 'end'
  }>(),
  {
    modelValue: '',
    side: 'top',
    align: 'center',
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
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

onMounted(() => {
  if (props.setDefault && !props.modelValue) setRandom()
})

function selectEmoji(value: string, close?: () => void) {
  emit('update:modelValue', value)
  emit('select', value)
  close?.()
}

function setRandom() {
  selectEmoji(gemoji[getRandomNumber(0, gemoji.length - 1)].emoji)
}

defineExpose({ setRandom })
</script>
