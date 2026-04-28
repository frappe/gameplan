<template>
  <div class="h-full touch-pan-y">
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
        :selectable="selectable"
        :selected="selectedDiscussions.includes(discussion.name)"
        @toggle-selection="toggleSelection"
      />
    </div>

    <DiscussionRow
      v-for="(discussion, i) of discussions.data"
      :key="discussion.name"
      :discussion="discussion"
      :index="Number(i)"
      :total="discussions.data?.length || 0"
      :showSpaceName="!filters || !filters.project"
      :selectable="selectable"
      :selected="selectedDiscussions.includes(discussion.name)"
      @toggle-selection="toggleSelection"
    />
    <div class="px-2 sm:px-0">
      <EmptyStateBox class="mx-3" v-if="!discussions.loading && discussions.data?.length === 0">
        <span class="lucide-coffee h-7 w-7 text-ink-gray-4" />
        No discussions
      </EmptyStateBox>
      <div class="flex items-center justify-center p-3" v-if="discussions.hasNextPage">
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
import { UseDiscussionOptions, useDiscussions } from '@/data/discussions'
import DiscussionRow from './DiscussionRow.vue'
import EmptyStateBox from './EmptyStateBox.vue'

interface Props {
  filters: UseDiscussionOptions['filters']
  orderBy?: UseDiscussionOptions['orderBy']
  cacheKey?: string
  showPinned?: boolean
  selectable?: boolean
  selectedDiscussions?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  showPinned: true,
  selectable: false,
  selectedDiscussions: () => [],
})

const emit = defineEmits<{
  (e: 'toggle-selection', name: string): void
}>()

const discussions = useDiscussions({
  filters: props.filters,
  orderBy: props.orderBy,
  cacheKey: props.cacheKey,
})

const pinnedDiscussions = useDiscussions({
  filters: () => {
    const baseFilters = toValue(props.filters)

    // If viewing a specific space (project filter exists)
    if (baseFilters?.project) {
      // Show only space-scoped pins for this specific project
      return {
        ...baseFilters,
        pinned_at: ['is', 'set'],
        pin_scope: 'Space',
      }
    } else {
      // When viewing all discussions/global view, show only global pins
      return {
        ...baseFilters,
        pinned_at: ['is', 'set'],
        pin_scope: 'Global',
      }
    }
  },
  orderBy: 'pinned_at desc' as OrderBy,
  limit: 99999,
  cacheKey: props.cacheKey ? ['pinned', props.cacheKey] : undefined,
  immediate: props.showPinned,
})

const filters = computed(() => toValue(props.filters))

function toggleSelection(name: string) {
  emit('toggle-selection', name)
}

defineExpose({ discussions, pinnedDiscussions })
</script>
