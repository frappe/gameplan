<template>
  <div>
    <div class="flex select-none gap-1.5 flex-wrap">
      <Motion
        as="button"
        aria-label="Add a reaction"
        :disabled="isLoading"
        @click="show = true"
        class="flex h-full items-center justify-center rounded-full bg-surface-gray-2 px-2 py-1 text-ink-gray-6 transition hover:bg-surface-gray-3"
        :whileTap="{ scale: 0.95 }"
        :whileHover="{ scale: 1.03 }"
      >
        <ReactionFaceIcon />
      </Motion>
      <div v-for="(reactions, emoji) in reactionsCount" :key="emoji">
        <Motion
          as="button"
          class="flex items-center justify-center rounded-full px-2 py-1 text-sm transition"
          :class="[
            reactions.userReacted
              ? 'bg-surface-amber-2 text-amber-700 hover:bg-amber-200'
              : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3',
          ]"
          @click="show = true"
          :whileTap="{ scale: 0.96 }"
          :whileHover="{ scale: 1.03 }"
          :whilePress="{ scale: 1.1 }"
        >
          <img v-if="isImageEmoji(emoji)" :src="emoji" alt="" class="mr-1 size-4 object-contain" />
          <template v-else>{{ emoji }}&nbsp;</template>
          {{ reactions.count }}
        </Motion>
      </div>
    </div>
    <BottomSheet title="Reactions" v-model:open="show">
      <div class="border-b px-4 pb-4">
        <div class="grid grid-cols-5 items-center justify-center gap-2">
          <Motion
            as="button"
            v-for="emoji in standardEmojis"
            :key="emoji"
            class="px-1 py-2 rounded"
            :class="[
              hasUserReacted(emoji)
                ? 'bg-surface-amber-2'
                : 'bg-surface-sidebar hover:bg-surface-gray-2',
            ]"
            @click="toggleReaction(emoji)"
            :disabled="isLoading"
            :whileTap="{ scale: 0.9 }"
            :whileHover="{ scale: 1.05 }"
            :whilePress="{ scale: 1.05 }"
          >
            <img
              v-if="isImageEmoji(emoji)"
              :src="emoji"
              alt=""
              class="mx-auto size-6 object-contain"
            />
            <span v-else class="font-[emoji] text-4xl">
              {{ emoji }}
            </span>
          </Motion>
        </div>
      </div>
      <div class="p-4">
        <AnimatePresence :initial="false">
          <Motion
            v-for="(reactions, emoji) in reactionsCount"
            :key="emoji"
            class="flex py-2 items-start"
            :initial="{ opacity: 0, y: 8 }"
            :animate="{ opacity: 1, y: 0 }"
            :exit="{ opacity: 0, y: 0 }"
            :transition="{ type: 'spring', stiffness: 320, damping: 26 }"
          >
            <div class="mr-2 flex w-14 items-center justify-center gap-1 text-center">
              <img v-if="isImageEmoji(emoji)" :src="emoji" alt="" class="size-6 object-contain" />
              <span v-else class="text-4xl font-[emoji]"> {{ emoji }}</span>
              <span class="text-p-xl text-ink-gray-4"> ({{ reactions.count }}) </span>
            </div>
            <span class="text-p-xl flex-1 text-ink-gray-6">
              {{ toolTipText(reactions) }}
            </span>
          </Motion>
        </AnimatePresence>
      </div>
    </BottomSheet>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { AnimatePresence, Motion } from 'motion-v'
import ReactionFaceIcon from './ReactionFaceIcon.vue'
import { BottomSheet } from 'frappe-ui'
import { isImageEmoji } from '@/utils/emoji'
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
