<template>
  <div class="h-full touch-pan-y">
    <div class="mb-5" v-if="pinnedDiscussions.data?.length">
      <div class="px-3 flex items-center space-x-1 mb-2">
        <Pin class="h-4 w-4 text-ink-gray-4" />
        <span class="text-ink-gray-8 text-base"> Pinned </span>
      </div>
      <List :selectable="selectable" v-model:selection="selectedDiscussions" :class="listClass">
        <DiscussionRow
          v-for="discussion of pinnedDiscussions.data"
          :key="discussion.name"
          :discussion="discussion"
          :showSpaceName="!filters || !filters.project"
        />
      </List>
    </div>

    <template v-if="isInitialLoading">
      <ListRowSkeleton
        v-for="index in skeletonRowCount"
        :key="index"
        :show-separator="index < skeletonRowCount"
        label="Loading discussion"
      />
    </template>

    <OfflineContentFallback
      v-if="loadFailure"
      class="mx-auto mt-6 max-w-2xl px-6"
      v-bind="loadFailure"
      @retry="discussions.reload()"
    />

    <List :selectable="selectable" v-model:selection="selectedDiscussions" :class="listClass">
      <DiscussionRow
        v-for="discussion of discussions.data"
        :key="discussion.bookmark || discussion.name"
        :discussion="discussion"
        :showSpaceName="!filters || !filters.project"
      />
    </List>
    <div class="px-2 sm:px-0">
      <EmptyStateBox class="mx-3" v-if="!discussions.loading && discussions.data?.length === 0">
        <span class="lucide-coffee h-7 w-7 text-ink-gray-4" />
        No discussions
      </EmptyStateBox>
      <div class="flex items-center justify-center p-3" v-if="showLoadMoreButton">
        <Button
          icon-left="lucide-refresh-cw"
          @click="discussions.next"
          :loading="discussions.loading"
        >
          {{ discussions.loading ? 'Loading...' : 'Load more' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toValue } from 'vue'
import type { OrderBy } from 'frappe-ui'
import { List } from 'frappe-ui/list'
import { UseDiscussionOptions, useDiscussions, pinScopes, pinnedFeedKey } from '@/data/discussions'
import DiscussionRow from './DiscussionRow.vue'
import ListRowSkeleton from './ListRowSkeleton.vue'
import EmptyStateBox from './EmptyStateBox.vue'
import OfflineContentFallback from './OfflineContentFallback.vue'
import { useLoadFailure } from '@/data/loadFailure'
import Pin from './icons/Pin.vue'

interface Props {
  filters: UseDiscussionOptions['filters']
  orderBy?: UseDiscussionOptions['orderBy']
  cacheKey?: string
  showPinned?: boolean
  selectable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showPinned: true,
  selectable: false,
})

const selectedDiscussions = defineModel<string[]>('selectedDiscussions', { default: () => [] })

// Match the hand-rolled DiscussionRow geometry: 12px gap + 16px row padding
// on mobile, 16px gap + the default 12px padding on desktop.
const listClass = 'max-sm:list-gap-3 sm:list-gap-4 max-sm:list-row-px-4'

const discussions = useDiscussions({
  filters: props.filters,
  orderBy: props.orderBy,
  cacheKey: props.cacheKey,
})

const pinnedDiscussions = useDiscussions({
  filters: () => {
    const baseFilters = toValue(props.filters)

    return {
      ...baseFilters,
      pinned_at: ['is', 'set'],
      pin_scope: ['in', pinScopes(Boolean(baseFilters?.project))],
    }
  },
  orderBy: 'pinned_at desc' as OrderBy,
  limit: 99999,
  cacheKey: props.cacheKey ? pinnedFeedKey(props.cacheKey) : undefined,
  immediate: props.showPinned,
})

const filters = computed(() => toValue(props.filters))
const skeletonRowCount = 3
const isInitialLoading = computed(() => discussions.loading && !discussions.data?.length)
const loadFailure = useLoadFailure(discussions, 'discussions')
const showLoadMoreButton = computed(
  () => discussions.hasNextPage && !isInitialLoading.value && !loadFailure.value,
)

defineExpose({ discussions, pinnedDiscussions })
</script>
