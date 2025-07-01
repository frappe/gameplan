<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
  >
    <Breadcrumbs class="h-7" :items="[{ label: 'Discussions', route: { name: 'Discussions' } }]" />
    <Button variant="solid" :route="{ name: 'NewDiscussion' }">
      <template #prefix><LucidePlus class="h-4 w-4" /></template>
      Add new
    </Button>
  </header>
  <div class="mx-auto max-w-4xl pt-5 sm:px-5">
    <LastPostReminder class="px-3 mb-3" />

    <div class="overflow-x-auto flex gap-2 px-3 py-1 mb-3 items-center">
      <TabButtons :buttons="feedOptions" v-model="currentFeedType" />
      <div class="ml-auto flex space-x-2" v-if="currentFeedType !== 'drafts'">
        <Button
          v-if="discussionListRef?.discussions?.loading"
          :loading="discussionListRef?.discussions?.loading"
        >
          Loading...
        </Button>
        <Select class="pr-7 shrink-0 min-w-28" :options="orderOptions" v-model="orderBy" />
      </div>
    </div>
    <div v-if="currentFeedType == 'drafts'">
      <DraftDiscussions />
    </div>
    <KeepAlive v-else>
      <DiscussionList
        ref="discussionListRef"
        routeName="ProjectDiscussion"
        :filters="filters"
        :orderBy="orderBy"
        :cacheKey="`HomeDiscussions-${currentFeedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { Breadcrumbs, Select, TabButtons, usePageMeta } from 'frappe-ui'
import type { OrderBy } from 'frappe-ui/src/data-fetching/useList/types'
import DiscussionList from '@/components/DiscussionList.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import DraftDiscussions from '@/components/DraftDiscussions.vue'
import { useRouter } from 'vue-router'

type FeedType = 'following' | 'participating' | 'recent' | 'bookmarks' | 'drafts' | 'unread'

interface Props {
  feedType?: FeedType
}

const props = withDefaults(defineProps<Props>(), {
  feedType: 'recent',
})

const router = useRouter()
const orderBy = ref<OrderBy>('last_post_at desc')
const discussionListRef = useTemplateRef('discussionListRef')

const currentFeedType = computed({
  get: () => props.feedType,
  set: (value: FeedType) => {
    router.push({ name: 'DiscussionsTab', params: { feedType: value } })
  },
})

const filters = computed(() => {
  return currentFeedType.value ? { feed_type: currentFeedType.value } : undefined
})

const feedOptions = [
  {
    label: 'All',
    value: 'recent',
  },
  {
    label: 'Unread',
    value: 'unread',
  },
  {
    label: 'Following',
    value: 'following',
  },
  {
    label: 'Participating',
    value: 'participating',
  },
  {
    label: 'Bookmarks',
    value: 'bookmarks',
  },
  {
    label: 'Drafts',
    value: 'drafts',
  },
]

const orderOptions = [
  {
    label: 'Sort by',
    value: '' as const,
    disabled: true,
  },
  {
    label: 'Last post',
    value: 'last_post_at desc' as OrderBy,
  },
  {
    label: 'Created',
    value: 'creation desc' as OrderBy,
  },
]

usePageMeta(() => {
  return {
    title: 'Discussions',
  }
})
</script>
