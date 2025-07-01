<template>
  <div class="h-full">
    <div class="mb-5" v-if="pinnedDiscussions.data?.length">
      <div class="px-3 flex items-center space-x-1 mb-2">
        <Pin class="h-4 w-4 text-ink-gray-4" />
        <span class="text-ink-gray-8 text-base"> Pinned </span>
      </div>
      <DiscussionRow
        v-for="(discussion, index) of pinnedDiscussions.data"
        :key="discussion.name"
        :discussion="discussion"
        :index="Number(index)"
        :total="pinnedDiscussions.data.length"
        :showSpaceName="!filters || !filters.project"
      />
    </div>

    <DiscussionRow
      v-for="(discussion, i) of discussions.data"
      :key="discussion.name"
      :discussion="discussion"
      :index="Number(i)"
      :total="discussions.data?.length || 0"
      :showSpaceName="!filters || !filters.project"
    />
    <div class="px-2 sm:px-0">
      <EmptyStateBox class="mx-3" v-if="!discussions.loading && discussions.data?.length === 0">
        <LucideCoffee class="h-7 w-7 text-ink-gray-4" />
        No discussions
      </EmptyStateBox>
      <div class="flex items-center justify-center p-3" v-if="discussions.hasNextPage">
        <Button @click="discussions.next" :loading="discussions.loading">
          <template #prefix>
            <LucideRefreshCw class="h-4 w-4" />
          </template>
          {{ discussions.loading ? 'Loading...' : 'Load more' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toValue } from 'vue'
import type { OrderBy } from 'frappe-ui/src/data-fetching/useList/types'
import { UseDiscussionOptions, useDiscussions } from '@/data/discussions'
import DiscussionRow from './DiscussionRow.vue'
import EmptyStateBox from './EmptyStateBox.vue'

interface Props {
  filters: UseDiscussionOptions['filters']
  orderBy?: UseDiscussionOptions['orderBy']
  cacheKey?: string
  showPinned?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showPinned: true,
})

const discussions = useDiscussions({
  filters: props.filters,
  orderBy: props.orderBy,
  cacheKey: props.cacheKey,
})

const pinnedDiscussions = useDiscussions({
  filters: () => ({ ...toValue(props.filters), pinned_at: ['is', 'set'] }),
  orderBy: 'pinned_at desc' as OrderBy,
  limit: 99999,
  cacheKey: props.cacheKey ? ['pinned', props.cacheKey] : undefined,
  immediate: props.showPinned,
})

const filters = computed(() => toValue(props.filters))

defineExpose({ discussions })
</script>
