<template>
  <div class="flex select-none items-stretch space-x-1.5">
    <Popover class="h-full">
      <template #target="{ togglePopover, isOpen }">
        <button
          aria-label="Add a reaction"
          :disabled="isLoading"
          @click="togglePopover()"
          class="flex h-full items-center justify-center rounded-full bg-gray-100 px-2 py-1 text-gray-700 transition hover:bg-gray-200"
          :class="{ 'bg-gray-200': isOpen }"
        >
          <ReactionFaceIcon />
        </button>
      </template>
      <template #body-main="{ togglePopover }">
        <div class="mt-1 inline-flex p-1">
          <div class="grid grid-cols-10 items-center space-x-0.5">
            <button
              class="h-6 w-6 rounded hover:bg-gray-50"
              v-for="emoji in standardEmojis"
              :key="emoji"
              @click="
                () => {
                  toggleReaction(emoji)
                  togglePopover()
                }
              "
              :disabled="isLoading"
            >
              {{ emoji }}
            </button>
          </div>
        </div>
      </template>
    </Popover>
    <Tooltip v-for="(reactions, emoji) in reactionsCount" :key="emoji">
      <button
        class="flex items-center justify-center rounded-full px-2 py-1 text-sm transition"
        :class="[
          reactions.userReacted
            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
        ]"
        @click="toggleReaction(emoji)"
      >
        {{ emoji }} {{ reactions.count }}
      </button>
      <template #body>
        <div
          class="max-w-[30ch] rounded-lg border border-gray-100 bg-gray-800 px-2 py-1 text-center text-xs text-white shadow-xl"
        >
          {{ toolTipText(reactions) }}
        </div>
      </template>
    </Tooltip>
  </div>
</template>
<script setup lang="ts">
import { Popover, Tooltip } from 'frappe-ui'
import ReactionFaceIcon from './ReactionFaceIcon.vue'
const props = defineProps<{
  reactionsCount: Record<string, { count: number; userReacted: boolean }>
  toggleReaction: (emoji: string) => void
  toolTipText: (reactions: { count: number; userReacted: boolean }) => string
  standardEmojis: string[]
  isLoading: boolean
}>()
</script>
