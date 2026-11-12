<template>
  <PageHeaderMobile class="sm:hidden" :title="feedTitle">
    <template #prefix>
      <PageHeaderBackButton :fallback-route="{ name: 'Home' }" />
    </template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <span class="min-w-0 truncate px-0.5 py-1 text-lg-medium text-ink-gray-9">All Discussions</span>
    <Button variant="solid" icon-left="lucide-plus" :route="{ name: 'LegacyNewDiscussion' }">
      Add new
    </Button>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <LastPostReminder class="mb-3" />

    <div class="mb-3 flex items-center justify-between gap-2">
      <TabButtons class="feed-tabs" :options="feedTabs" v-model="currentFeed" size="sm">
        <template #suffix="{ button }">
          <span
            v-if="button.value === 'unread' && unreadCount > 0"
            class="ml-1 text-xs text-ink-gray-5"
          >
            {{ unreadCount }}
          </span>
        </template>
      </TabButtons>
      <DiscussionSortDropdown />
    </div>

    <KeepAlive>
      <DiscussionList
        class="-mx-3"
        :filters="filters"
        :orderBy="() => discussionOrderBy"
        :showPinned="false"
        showCommunity
        :cacheKey="`AllDiscussions-${feedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Button,
  PageHeader,
  PageHeaderBackButton,
  PageHeaderMobile,
  TabButtons,
  usePageMeta,
} from 'frappe-ui'
import { useRouter } from 'vue-router'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionSortDropdown from '@/components/DiscussionSortDropdown.vue'
import { discussionOrderBy } from '@/data/discussionSort'
import LastPostReminder from '@/components/LastPostReminder.vue'
import { activeCommunities } from '@/data/communities'
import { feedTabs, feedTitles, type FeedType } from '@/data/discussionFeeds'
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
  set(feedType) {
    if (!feedType || feedType === props.feedType) return
    router.push(
      feedType === 'recent'
        ? { name: 'AllDiscussions' }
        : { name: 'AllDiscussionsTab', params: { feedType } },
    )
  },
})

usePageMeta(() => ({ title: feedTitle.value }))
</script>
