<template>
  <div class="flex select-none flex-wrap items-stretch gap-1.5">
    <HoverCard
      v-if="!readOnlyMode && !isAnonymous"
      v-model:open="isPickerOpen"
      side="bottom"
      align="start"
      @pointer-down-outside="onPointerDownOutside"
    >
      <template #trigger>
        <button
          aria-label="Add a reaction"
          :disabled="isLoading"
          class="flex h-full items-center justify-center rounded-full bg-surface-gray-2 px-2 py-1 text-ink-gray-6 transition hover:bg-surface-gray-3 print:hidden"
          :class="{ 'bg-surface-gray-3': isPickerOpen }"
          @click="isPickerOpen = true"
        >
          <span class="lucide-smile-plus" aria-label="React with emoji" />
        </button>
      </template>
      <div class="inline-flex p-1">
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
      </div>
    </HoverCard>
    <!-- One provider for the whole row: after the first tooltip opens, moving
         along the pills shows the next reactor list with no re-delay. -->
    <template v-if="showTooltips">
      <TooltipProvider>
        <template v-for="(reactions, emoji) in reactionsCount" :key="emoji">
          <Tooltip v-if="toolTipText(reactions)">
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
            <template #content>
              <div class="max-w-[30ch] text-center text-p-xs">
                {{ toolTipText(reactions) }}
              </div>
            </template>
          </Tooltip>
          <button
            v-else
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
        </template>
      </TooltipProvider>
    </template>
    <template v-else>
      <button
        v-for="(reactions, emoji) in reactionsCount"
        :key="emoji"
        class="flex cursor-default items-center justify-center rounded-full px-2 py-1 text-sm transition"
        :class="[
          reactions.userReacted
            ? 'bg-surface-amber-2 text-amber-700'
            : 'bg-surface-gray-2 text-ink-gray-6',
        ]"
      >
        <img v-if="isImageEmoji(emoji)" :src="emoji" alt="" class="mr-1 size-4 object-contain" />
        <template v-else>{{ emoji }}&nbsp;</template>
        {{ reactions.count }}
      </button>
    </template>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, HoverCard, Tooltip, TooltipProvider } from 'frappe-ui'
import { isImageEmoji } from '@/utils/emoji'
import { isAnonymousVisitor } from '@/utils/publicAccess'

const props = defineProps<{
  reactionsCount: Record<string, { count: number; userReacted: boolean }>
  toggleReaction: (emoji: string) => void
  toolTipText: (reactions: { count: number; userReacted: boolean }) => string
  standardEmojis: string[]
  isLoading: boolean
  readOnlyMode?: boolean
}>()

const isAnonymous = computed(() => isAnonymousVisitor())
const showTooltips = computed(() => !props.readOnlyMode && !isAnonymous.value)
const isPickerOpen = ref(false)

function selectEmoji(emoji: string) {
  props.toggleReaction(emoji)
  isPickerOpen.value = false
}

// Clicking the trigger counts as a pointer-down "outside" the card, which would
// otherwise dismiss it (then hover/click reopens it — a visible flash). Keep the
// card open instead; it still closes on mouse leave or after a selection.
function onPointerDownOutside(event: Event) {
  event.preventDefault()
}
</script>
