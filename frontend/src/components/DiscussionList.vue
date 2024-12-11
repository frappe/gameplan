<template>
  <div class="h-full">
    <div class="mb-5" v-if="pinnedDiscussions.length">
      <div class="px-3 flex items-center space-x-1 mb-2">
        <Pin class="h-4 w-4 text-ink-gray-4" />
        <span class="text-ink-gray-9 text-base"> Pinned </span>
      </div>
      <DiscussionRow
        v-for="(discussion, index) in pinnedDiscussions"
        :key="discussion.name"
        :discussion="discussion"
        :index="index"
        :total="pinnedDiscussions.length"
        :showSpaceName="!filters || !filters.project"
      />
    </div>

    <DiscussionRow
      v-for="(discussion, index) in unpinnedDiscussions"
      :key="discussion.name"
      :discussion="discussion"
      :index="index"
      :total="unpinnedDiscussions.length"
      :showSpaceName="!filters || !filters.project"
    />
    <div class="px-2 sm:px-0">
      <EmptyStateBox v-if="!discussions.list.loading && discussions.data.length === 0">
        <LucideCoffee class="h-7 w-7 text-ink-gray-4" />
        No discussions
      </EmptyStateBox>
      <div
        class="flex items-center justify-center p-3"
        v-if="!hideLoadMore && discussions.hasNextPage"
      >
        <Button @click="discussions.next" :loading="discussions.list.loading">
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
import { computed } from 'vue'
import { useDiscussions } from '@/data/discussions'
import DiscussionRow from './DiscussionRow.vue'
import EmptyStateBox from './EmptyStateBox.vue'

interface Discussion {
  name: number
  pinned_at?: string
  last_post_at: string
  last_visit?: string
  unread?: boolean
}

interface ListOptions {
  filters?: Record<string, any>
  pageLength?: number
  orderBy?: string
}

const props = defineProps({
  listOptions: {
    type: Object as () => ListOptions,
    default: () => ({}),
  },
  hideLoadMore: {
    type: Boolean,
    default: false,
  },
})

const discussions = useDiscussions(props.listOptions)

const pinnedDiscussions = computed(() =>
  (discussions.value.data || []).filter((d: Discussion) => d.pinned_at),
)

const unpinnedDiscussions = computed(() =>
  (discussions.value.data || []).filter((d: Discussion) => !d.pinned_at),
)

const filters = computed(() => props.listOptions.filters)

defineExpose({ discussions })
</script>
