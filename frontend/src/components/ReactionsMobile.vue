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
    <BottomSheet :title="isBrowsingAllEmojis ? 'All emoji' : 'Reactions'" v-model:open="show">
      <!--
        The full picker takes over the sheet body instead of opening a second
        sheet on top of this one. The header row is the way back to the quick
        reactions.
      -->
      <div v-if="isBrowsingAllEmojis" class="flex h-full flex-col bg-surface-base">
        <div class="border-b px-2 pb-2">
          <Button variant="ghost" label="Quick reactions" @click="collapse">
            <template #prefix>
              <span class="lucide-chevron-left size-4" aria-hidden="true" />
            </template>
          </Button>
        </div>
        <EmojiPickerPanel class="min-h-0 flex-1" @select="pickFromAllEmojis" />
      </div>
      <template v-else>
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
            <Motion
              as="button"
              aria-label="Browse all emoji"
              class="flex items-center justify-center rounded bg-surface-sidebar px-1 py-2 text-ink-gray-6 hover:bg-surface-gray-2"
              @click="browseAllEmojis"
              :whileTap="{ scale: 0.9 }"
              :whileHover="{ scale: 1.05 }"
            >
              <span class="lucide-plus size-6" aria-hidden="true" />
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
      </template>
    </BottomSheet>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { AnimatePresence, Motion } from 'motion-v'
import ReactionFaceIcon from './ReactionFaceIcon.vue'
import { BottomSheet, Button } from 'frappe-ui'
import EmojiPickerPanel from '@/components/EmojiPickerPanel.vue'
import { isImageEmoji } from '@/utils/emoji'
import { useReactionPicker } from '@/utils/useReactionPicker'

const props = defineProps<{
  reactionsCount: Record<string, { count: number; userReacted: boolean }>
  toggleReaction: (emoji: string) => void
  toolTipText: (reactions: { count: number; userReacted: boolean }) => string
  standardEmojis: string[]
  isLoading: boolean
}>()

let show = ref(false)

// Picking from the full list drops back to the quick reactions rather than
// closing the sheet, so the new reaction is visible in the list below it.
const { isBrowsingAllEmojis, browseAllEmojis, collapse, pickFromAllEmojis } = useReactionPicker({
  toggleReaction: (emoji) => props.toggleReaction(emoji),
})

watch(show, (open) => {
  if (!open) collapse()
})

function hasUserReacted(emoji) {
  return props.reactionsCount[emoji]?.userReacted
}
</script>
