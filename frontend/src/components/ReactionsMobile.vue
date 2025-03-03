<template>
  <div>
    <div class="flex select-none gap-1.5 flex-wrap">
      <button
        aria-label="Add a reaction"
        :disabled="isLoading"
        @click="show = true"
        class="flex h-full items-center justify-center rounded-full bg-surface-gray-2 px-2 py-1 text-ink-gray-6 transition hover:bg-surface-gray-3"
      >
        <ReactionFaceIcon />
      </button>
      <div v-for="(reactions, emoji) in reactionsCount" :key="emoji">
        <button
          class="flex items-center justify-center rounded-full px-2 py-1 text-sm transition"
          :class="[
            reactions.userReacted
              ? 'bg-surface-amber-2 text-amber-700 hover:bg-amber-200'
              : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3',
          ]"
          @click="show = true"
        >
          {{ emoji }} {{ reactions.count }}
        </button>
      </div>
    </div>
    <ActionSheet v-model="show" title="Reactions">
      <div class="p-4 border-b">
        <div class="grid grid-cols-5 items-center justify-center gap-2">
          <button
            v-for="emoji in standardEmojis"
            :key="emoji"
            class="p-1 rounded font-[emoji] text-3xl text-center w-full"
            :class="[
              hasUserReacted(emoji)
                ? 'bg-surface-amber-2'
                : 'bg-surface-menu-bar hover:bg-surface-gray-2',
            ]"
            @click="
              () => {
                toggleReaction(emoji)
              }
            "
            :disabled="isLoading"
          >
            {{ emoji }}
          </button>
        </div>
      </div>
      <div class="p-4">
        <div v-for="(reactions, emoji) in reactionsCount" :key="emoji">
          <div class="flex py-2 items-start">
            <div class="mr-2 w-14 text-center">
              <span class="text-2xl font-[emoji]"> {{ emoji }}</span>
              <span class="text-p-lg text-ink-gray-4"> ({{ reactions.count }}) </span>
            </div>
            <span class="text-p-lg flex-1 text-ink-gray-6">
              {{ toolTipText(reactions) }}
            </span>
          </div>
        </div>
      </div>
    </ActionSheet>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import ReactionFaceIcon from './ReactionFaceIcon.vue'
import ActionSheet from './ActionSheet.vue'
const props = defineProps<{
  reactionsCount: Record<string, { count: number; userReacted: boolean }>
  toggleReaction: (emoji: string) => void
  toolTipText: (reactions: { count: number; userReacted: boolean }) => string
  standardEmojis: string[]
  isLoading: boolean
}>()

let show = ref(false)

function hasUserReacted(emoji) {
  return props.reactionsCount[emoji]?.userReacted
}
</script>
