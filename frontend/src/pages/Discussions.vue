<template>
  <PageHeader>
    <Breadcrumbs class="h-7" :items="[{ label: 'Discussions', route: { name: 'Discussions' } }]" />
    <Button variant="solid" icon-left="lucide-plus" :route="{ name: 'NewDiscussion' }">
      Add new
    </Button>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <LastPostReminder class="mb-3" />

    <div class="overflow-x-auto flex gap-2 py-1 mb-3 items-center -mx-3 px-3">
      <TabButtons :buttons="feedOptions" v-model="currentFeedType" />
      <div class="ml-auto flex space-x-2" v-if="currentFeedType !== 'drafts'">
        <Button
          v-if="discussionListRef?.discussions?.loading"
          :loading="discussionListRef?.discussions?.loading"
        >
          Loading...
        </Button>
        <Select class="shrink-0 !w-fit" :options="orderOptions" v-model="orderBy" />
      </div>
    </div>
    <KeepAlive>
      <DiscussionList
        class="-mx-3"
        ref="discussionListRef"
        routeName="ProjectDiscussion"
        :filters="filters"
        :orderBy="() => orderBy"
        :cacheKey="`HomeDiscussions-${currentFeedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { Breadcrumbs, Select, TabButtons, usePageMeta } from 'frappe-ui'
import type { OrderBy } from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'
import PageHeader from '@/components/PageHeader.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import { useRouter } from 'vue-router'

type FeedType = 'following' | 'participating' | 'recent' | 'bookmarks' | 'unread'

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
]

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

usePageMeta(() => {
  return {
    title: 'Discussions',
  }
})
</script>
