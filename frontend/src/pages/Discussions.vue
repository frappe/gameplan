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
    <LastPostReminder class="px-3 mb-4" />

    <div class="mb-4 flex items-center px-3">
      <TabButtons :buttons="feedOptions" v-model="feedType" />
      <div class="ml-auto flex space-x-2" v-if="feedType !== 'drafts'">
        <Button
          v-if="$refs.discussionListRef?.discussions.loading"
          :loading="$refs.discussionListRef?.discussions.loading"
        >
          Loading...
        </Button>
        <Select class="pr-7" :options="orderOptions" v-model="orderBy" />
      </div>
    </div>
    <div v-if="feedType == 'drafts'">
      <DraftDiscussions />
    </div>
    <KeepAlive v-else>
      <DiscussionList
        ref="discussionListRef"
        routeName="ProjectDiscussion"
        :filters="filters"
        :orderBy="orderBy"
        :cacheKey="`HomeDiscussions-${feedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Breadcrumbs, Select, TabButtons, usePageMeta } from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import { useLocalStorage } from '@vueuse/core'
import DraftDiscussions from '@/components/DraftDiscussions.vue'

const feedType = useLocalStorage<'following' | 'participating' | 'recent' | 'bookmarks' | 'drafts'>(
  'homeFeedType',
  'following',
)
const orderBy = ref('last_post_at desc')

const filters = computed(() => {
  return feedType.value ? { feed_type: feedType.value } : null
})

const feedOptions = [
  {
    label: 'All',
    value: 'recent',
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
    value: '',
    disabled: true,
  },
  {
    label: 'Last post',
    value: 'last_post_at desc',
  },
  {
    label: 'Created',
    value: 'creation desc',
  },
]

usePageMeta(() => {
  return {
    title: 'Discussions',
  }
})
</script>
