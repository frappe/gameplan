<template>
  <PopoverRoot :open="store.popover.open" @update:open="onOpenChange">
    <PopoverAnchor v-if="store.popover.anchorEl" :reference="store.popover.anchorEl" />
    <PopoverPortal>
      <PopoverContent
        v-if="store.popover.anchorEl"
        side="bottom"
        align="start"
        :side-offset="4"
        :collision-padding="10"
        class="z-50 min-w-52 rounded-6 border bg-surface-elevation-2 p-1 shadow-xl"
      >
        <div class="px-2 pb-1 pt-1.5 text-xs text-ink-gray-5">Quoted by</div>
        <button
          v-for="item in store.popover.items"
          :key="item.quotingCommentId + item.creation"
          class="flex w-full items-center gap-2 rounded-4 px-2 py-1.5 text-start hover:bg-surface-gray-2 focus:outline-none focus-visible:ring focus-visible:ring-outline-gray-3"
          @click="select(item)"
        >
          <UserAvatar size="sm" :user="item.author" />
          <span class="text-base text-ink-gray-8">{{ fullName(item.author) }}</span>
          <span class="ms-auto ps-3 text-sm text-ink-gray-5">
            {{ dayjsLocal(item.creation).fromNow() }}
          </span>
        </button>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>
<script setup lang="ts">
import { PopoverAnchor, PopoverContent, PopoverPortal, PopoverRoot } from 'reka-ui'
import { dayjsLocal } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import { useUser } from '@/data/users'
import { type QuoteBacklink, type RichQuoteController } from './useRichQuotes'

const props = defineProps<{ store: RichQuoteController }>()
const emit = defineEmits<{ select: [quotingCommentId: string] }>()

function fullName(author: string) {
  return useUser(author).full_name?.trim() || author
}

function onOpenChange(open: boolean) {
  if (!open) props.store.closePopover()
}

function select(item: QuoteBacklink) {
  props.store.closePopover()
  emit('select', item.quotingCommentId)
}
</script>
