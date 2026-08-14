<template>
  <PageHeaderMobile v-if="communityState.doc" class="sm:hidden" :title="feedTitle">
    <template #prefix>
      <PageHeaderBackButton :to="{ name: 'Home' }" />
    </template>
    <button
      type="button"
      class="inline-flex max-w-full items-center gap-1 transition active:opacity-60"
      @click="menuOpen = true"
    >
      <PageHeaderMobileTitle :title="feedTitle" />
      <span class="size-4 shrink-0 text-ink-gray-5 lucide-chevron-down" aria-hidden="true" />
    </button>
  </PageHeaderMobile>

  <BottomSheet v-model:open="menuOpen" :title="community?.title || 'Community'">
    <CommunityMenu
      class="pb-6"
      :communityId="communityId"
      :activeFeedType="feedType"
      @navigate="menuOpen = false"
    />
  </BottomSheet>
  <PageHeader class="hidden sm:flex">
    <div class="flex min-w-0 items-center gap-1">
      <span class="min-w-0 truncate px-0.5 py-1 text-lg-medium text-ink-gray-9">Discussions</span>
    </div>
    <div class="flex items-center gap-2">
      <Button
        variant="solid"
        icon-left="lucide-plus"
        :route="{ name: 'NewDiscussion', params: { communityId } }"
      >
        Add new
      </Button>
    </div>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <LastPostReminder class="mb-3" />

    <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <TabButtons :options="feedTabs" v-model="currentFeed" size="sm">
        <template #suffix="{ button }">
          <span
            v-if="feedUnreadCount(String(button.value)) > 0"
            class="ms-1 text-xs text-ink-gray-5"
          >
            {{ feedUnreadCount(String(button.value)) }}
          </span>
        </template>
      </TabButtons>
      <Select class="shrink-0 !w-fit" :options="orderOptions" v-model="orderBy" />
    </div>

    <KeepAlive>
      <DiscussionList
        class="-mx-3"
        :filters="filters"
        :orderBy="() => orderBy"
        :cacheKey="`Discussions-${communityId}-${feedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  BottomSheet,
  PageHeader,
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeaderMobileTitle,
  Button,
  Select,
  TabButtons,
  usePageMeta,
} from 'frappe-ui'
import type { OrderBy } from 'frappe-ui'
import { useRouter } from 'vue-router'
import CommunityMenu from '@/components/CommunityMenu.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import { communityState } from '@/data/communityState'
import { useCommunity } from '@/data/communities'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { fetchParticipatingUnreadCount, getParticipatingUnreadCount } from '@/data/unreadCount'

type FeedType = 'recent' | 'unread' | 'participating'

interface Props {
  communityId: string
  feedType?: FeedType
}

const props = withDefaults(defineProps<Props>(), {
  feedType: 'recent',
})

const orderBy = ref<OrderBy>('last_post_at desc')
const menuOpen = ref(false)
const router = useRouter()

const filters = computed(() => ({
  team: props.communityId,
  feed_type: props.feedType,
}))

const feedTitles: Record<FeedType, string> = {
  recent: 'All Discussions',
  unread: 'Unread',
  participating: 'Participating',
}

const feedTitle = computed(() => feedTitles[props.feedType])

const community = useCommunity(() => props.communityId)
const communitySpaces = computed(() => {
  return (spaces.data || []).filter((space) => {
    return !space.archived_at && space.team === props.communityId
  })
})
const communityUnreadCount = computed(() => {
  return communitySpaces.value.reduce((total, space) => total + getSpaceUnreadCount(space.name), 0)
})
const participatingUnreadCount = computed(() => {
  return getParticipatingUnreadCount(props.communityId)
})
const feedTabs = computed(() => [
  {
    label: 'All Discussions',
    value: 'recent',
  },
  {
    label: 'Participating',
    value: 'participating',
  },
  {
    label: 'Unread',
    value: 'unread',
  },
])
const currentFeed = computed({
  get() {
    return props.feedType
  },
  set(feedType) {
    if (!feedType || feedType === props.feedType) return
    router.push(feedRoute(String(feedType) as FeedType))
  },
})
watch(
  () => props.communityId,
  (communityId) => {
    if (communityId) fetchParticipatingUnreadCount(communityId)
  },
  { immediate: true },
)

const orderOptions = [
  {
    label: 'Sort by',
    value: '' as const,
    disabled: true,
  },
  {
    label: 'Newest first',
    value: 'last_post_at desc' as OrderBy,
  },
  {
    label: 'Oldest first',
    value: 'last_post_at asc' as OrderBy,
  },
  {
    label: 'Creation date',
    value: 'creation desc' as OrderBy,
  },
]

function feedRoute(feedType: FeedType) {
  if (feedType === 'recent') {
    return { name: 'Discussions', params: { communityId: props.communityId } }
  }

  return {
    name: 'DiscussionsTab',
    params: { communityId: props.communityId, feedType },
  }
}

function feedUnreadCount(feedType: string) {
  if (feedType === 'unread') return communityUnreadCount.value
  if (feedType === 'participating') return participatingUnreadCount.value
  return 0
}

usePageMeta(() => ({ title: feedTitle.value }))
</script>
