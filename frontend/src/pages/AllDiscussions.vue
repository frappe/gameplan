<template>
  <PageHeaderMobile class="sm:hidden" :title="feedTitle">
    <template #prefix>
      <PageHeaderBackButton :fallback-route="{ name: 'Home' }" />
    </template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <span class="min-w-0 truncate px-0.5 py-1 text-lg-medium text-ink-gray-9">All discussions</span>
    <Button
      variant="solid"
      icon-left="lucide-plus"
      label="New discussion"
      :route="{ name: 'LegacyNewDiscussion' }"
    />
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <LastPostReminder class="mb-3" />

    <DiscussionFeedBar v-model="currentFeed" :counts="{ unread: unreadCount }" />

    <KeepAlive>
      <DiscussionList
        class="-mx-3"
        :filters="filters"
        :orderBy="() => discussionOrderBy"
        :showPinned="false"
        showCommunity
        :cacheKey="`AllDiscussions-${feedType}`"
        :key="JSON.stringify(filters)"
        :empty-state="feedEmptyStates[feedType]"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, PageHeader, PageHeaderBackButton, PageHeaderMobile, usePageMeta } from 'frappe-ui'
import { useRouter } from 'vue-router'
import DiscussionFeedBar from '@/components/DiscussionFeedBar.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import { activeCommunities } from '@/data/communities'
import { feedEmptyStates, feedTitles, type FeedType } from '@/data/discussionFeeds'
import { discussionOrderBy } from '@/data/discussionSort'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'

const props = withDefaults(defineProps<{ feedType?: FeedType }>(), {
  feedType: 'recent',
})

const router = useRouter()

const feedTitle = computed(() => feedTitles[props.feedType])

// Communities hidden from the rail stay out of this feed too: "all" means every
// community you have joined, not every one you can read.
const joinedCommunityIds = computed(() => activeCommunities.value.map((c) => c.name))

const filters = computed(() => {
  const team: [string, string[]] = ['in', joinedCommunityIds.value]
  return { team, feed_type: props.feedType }
})

const unreadCount = computed(() => {
  const joined = new Set(joinedCommunityIds.value)
  return (spaces.data || []).reduce((total, space) => {
    if (space.archived_at || !space.team || !joined.has(space.team)) return total
    return total + getSpaceUnreadCount(space.name)
  }, 0)
})

const currentFeed = computed({
  get: () => props.feedType,
  set(feedType: FeedType) {
    if (feedType === props.feedType) return
    router.push(
      feedType === 'recent'
        ? { name: 'AllDiscussions' }
        : { name: 'AllDiscussionsTab', params: { feedType } },
    )
  },
})

usePageMeta(() => ({ title: feedTitle.value }))
</script>
