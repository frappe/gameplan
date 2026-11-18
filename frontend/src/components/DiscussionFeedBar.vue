<template>
  <!-- The feed tabs and the sort, shared by the community, all-communities and space pages
       so the list below starts at the same height on each. -->
  <div class="mb-3 flex items-center justify-between gap-2">
    <TabButtons class="feed-tabs" :options="feedTabs" v-model="currentFeed" size="sm">
      <template #suffix="{ button }">
        <span v-if="countFor(button.value)" class="ml-1 text-xs text-ink-gray-5">
          {{ countFor(button.value) }}
        </span>
      </template>
    </TabButtons>
    <DiscussionSortDropdown :mark-all-as-read="canMarkAllAsRead ? onMarkAllAsRead : undefined" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TabButtons } from 'frappe-ui'
import DiscussionSortDropdown from '@/components/DiscussionSortDropdown.vue'
import { feedTabs, isFeedType, type FeedType } from '@/data/discussionFeeds'

const props = defineProps<{
  /** Unread counts shown after a tab's label. A tab with no count, or 0, shows none. */
  counts?: Partial<Record<FeedType, number>>
  /** Listening to `mark-all-as-read` adds "Mark all as read…" to the phone's feed menu. */
  onMarkAllAsRead?: () => void
}>()

const feed = defineModel<FeedType>({ required: true })

const currentFeed = computed({
  get: () => feed.value,
  set(value: string | number | undefined) {
    const next = String(value)
    if (isFeedType(next)) feed.value = next
  },
})

// Offered while the feed has something unread, whichever tab is open.
const canMarkAllAsRead = computed(() => countFor('unread') > 0)

function countFor(value: string | number) {
  const key = String(value)
  return isFeedType(key) ? props.counts?.[key] || 0 : 0
}
</script>
