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
    <!-- Desktop marks a feed read from the community and space menus, which a phone does not
         have. Sorting the Unread tab matters less, so on a phone its sort icon becomes this. -->
    <Button
      v-if="showMarkAllAsRead"
      size="md"
      icon="lucide-check-check text-ink-gray-6"
      label="Mark all as read"
      :disabled="!countFor('unread')"
      @click="onMarkAllAsRead"
    />
    <DiscussionSortDropdown v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, TabButtons } from 'frappe-ui'
import DiscussionSortDropdown from '@/components/DiscussionSortDropdown.vue'
import { feedTabs, isFeedType, type FeedType } from '@/data/discussionFeeds'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  /** Unread counts shown after a tab's label. A tab with no count, or 0, shows none. */
  counts?: Partial<Record<FeedType, number>>
  /** Listening to `mark-all-as-read` gives the phone's Unread tab a "Mark all as read" button. */
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

const isMobile = useIsMobile()
const showMarkAllAsRead = computed(
  () => isMobile.value && feed.value === 'unread' && Boolean(props.onMarkAllAsRead),
)

function countFor(value: string | number) {
  const key = String(value)
  return isFeedType(key) ? props.counts?.[key] || 0 : 0
}
</script>
