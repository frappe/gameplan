<template>
  <div class="flex select-none flex-wrap items-stretch gap-1.5">
    <HoverCard
      v-model:open="cardOpen"
      side="bottom"
      align="start"
      @pointer-down-outside="onPointerDownOutside"
      @escape-key-down="closePicker"
    >
      <template #trigger>
        <button
          ref="trigger"
          aria-label="Add a reaction"
          :disabled="isLoading"
          class="flex h-full items-center justify-center rounded-full bg-surface-gray-2 px-2 py-1 text-ink-gray-6 transition hover:bg-surface-gray-3 print:hidden"
          :class="{ 'bg-surface-gray-3': cardOpen }"
          @click="cardOpen = true"
        >
          <span class="lucide-smile-plus" aria-label="React with emoji" />
        </button>
      </template>
      <div class="flex flex-col bg-inherit">
        <div class="flex items-center gap-1 p-1">
          <div class="grid grid-cols-10 items-center gap-0.5">
            <Button
              v-for="emoji in standardEmojis"
              :key="emoji"
              variant="ghost"
              size="xs"
              class="font-[emoji]"
              :disabled="isLoading"
              @click="selectEmoji(emoji)"
            >
              <template #icon>
                <img v-if="isImageEmoji(emoji)" :src="emoji" alt="" class="size-4 object-contain" />
                <span v-else class="text-lg">
                  {{ emoji }}
                </span>
              </template>
            </Button>
          </div>
          <div class="h-6 w-px shrink-0 bg-outline-gray-1" />
          <Button
            variant="ghost"
            size="sm"
            :aria-label="isBrowsingAllEmojis ? 'Back to quick reactions' : 'Browse all emoji'"
            @click="isBrowsingAllEmojis ? collapse() : browseAllEmojis()"
          >
            <template #icon>
              <span
                class="size-4"
                :class="isBrowsingAllEmojis ? 'lucide-chevron-up' : 'lucide-plus'"
                aria-hidden="true"
              />
            </template>
          </Button>
        </div>
        <EmojiPickerPanel
          v-if="isBrowsingAllEmojis"
          class="h-80 min-w-[18rem] border-t border-outline-gray-1"
          @select="pickFromAllEmojis"
        />
      </div>
    </HoverCard>
    <Tooltip v-for="(reactions, emoji) in reactionsCount" :key="emoji">
      <button
        class="flex items-center justify-center rounded-full px-2 py-1 text-sm transition"
        :class="[
          reactions.userReacted
            ? 'bg-surface-amber-2 text-amber-700 hover:bg-amber-200'
            : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3',
        ]"
        @click="toggleReaction(emoji)"
      >
        <img v-if="isImageEmoji(emoji)" :src="emoji" alt="" class="mr-1 size-4 object-contain" />
        <template v-else>{{ emoji }}&nbsp;</template>
        {{ reactions.count }}
      </button>
      <template #body>
        <div
          class="max-w-[30ch] rounded bg-surface-gray-10 px-2 py-1 text-center text-p-xs text-ink-base shadow-xl"
        >
          {{ toolTipText(reactions) }}
        </div>
      </template>
    </Tooltip>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { Button, HoverCard, Tooltip } from 'frappe-ui'
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

const trigger = useTemplateRef<HTMLElement>('trigger')
const isPickerOpen = ref(false)

const { isBrowsingAllEmojis, browseAllEmojis, collapse, pickFromAllEmojis } = useReactionPicker({
  toggleReaction: (emoji) => props.toggleReaction(emoji),
  onPick: () => closePicker(),
})

// A hover card closes as soon as the pointer leaves it, which is right for the
// quick row but wrong once the full picker is open: searching and scrolling
// takes the cursor away from the card. While it is open, only an explicit
// dismissal (escape, an outside click, or picking an emoji) closes the card.
const cardOpen = computed({
  get: () => isPickerOpen.value,
  set: (value: boolean) => {
    if (!value && isBrowsingAllEmojis.value) return
    isPickerOpen.value = value
  },
})

function closePicker() {
  collapse()
  isPickerOpen.value = false
}

function selectEmoji(emoji: string) {
  props.toggleReaction(emoji)
  closePicker()
}

// Clicking the trigger counts as a pointer-down "outside" the card, which would
// otherwise dismiss it (then hover/click reopens it — a visible flash). Keep the
// card open for that one case; a real outside click still closes it.
function onPointerDownOutside(event: Event) {
  const originalEvent = (event as CustomEvent<{ originalEvent?: Event }>).detail?.originalEvent
  const target = originalEvent?.target
  if (target instanceof Node && trigger.value?.contains(target)) {
    event.preventDefault()
    return
  }
  closePicker()
}
</script>
