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

    <List :selectable="selectable" v-model:selection="selectedDiscussions" :class="listClass">
      <DiscussionRow
        v-for="discussion of discussions.data"
        :key="discussion.name"
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
import { UseDiscussionOptions, useDiscussions } from '@/data/discussions'
import DiscussionRow from './DiscussionRow.vue'
import ListRowSkeleton from './ListRowSkeleton.vue'
import EmptyStateBox from './EmptyStateBox.vue'
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

    if (baseFilters?.project) {
      // A community pin is a superset of a space pin — "Show in all <community>
      // discussions" has to include the discussion's own space, or the pin is
      // invisible everywhere the author looks for it. This also brings back every
      // pre-2025-10 pin, which set_default_pin_scope + rename_global_pin_scope_to_category
      // stamped `Category` without ever asking the user to pick a scope.
      return {
        ...baseFilters,
        pinned_at: ['is', 'set'],
        pin_scope: ['in', ['Space', 'Category']],
      }
    }

    return {
      ...baseFilters,
      pinned_at: ['is', 'set'],
      pin_scope: 'Category',
    }
  },
  orderBy: 'pinned_at desc' as OrderBy,
  limit: 99999,
  cacheKey: props.cacheKey ? ['pinned', props.cacheKey] : undefined,
  immediate: props.showPinned,
})

const filters = computed(() => toValue(props.filters))
const skeletonRowCount = 3
const isInitialLoading = computed(() => discussions.loading && !discussions.data?.length)
const showLoadMoreButton = computed(() => discussions.hasNextPage && !isInitialLoading.value)

defineExpose({ discussions, pinnedDiscussions })
</script>
