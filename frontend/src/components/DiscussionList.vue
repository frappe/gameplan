<template>
  <div class="h-full touch-pan-y">
    <template v-if="isInitialLoading">
      <ListRowSkeleton
        v-for="index in skeletonRowCount"
        :key="index"
        :show-separator="index < skeletonRowCount"
        label="Loading discussion"
      />
    </template>

    <!-- Pinned rows lead the list, marked by a pin icon rather than a heading. -->
    <List :selectable="selectable" v-model:selection="selectedDiscussions" :class="listClass">
      <DiscussionRow
        v-for="discussion of visiblePinnedDiscussions"
        :key="'pinned-' + discussion.name"
        :discussion="discussion"
        :showSpaceName="!filters || !filters.project"
        :showCommunityName="showCommunity"
        pinned
      />
      <DiscussionRow
        v-for="discussion of visibleDiscussions"
        :key="rowKey(discussion)"
        :discussion="discussion"
        :showSpaceName="!filters || !filters.project"
        :showCommunityName="showCommunity"
        :showCreatedAt="isSortedByCreation"
        :removable="removableBookmarks"
        @remove="removeBookmarkRow(discussion)"
      />
    </List>
    <div class="px-2 sm:px-0">
      <LoadError
        v-if="discussions.error && !discussions.data?.length"
        class="mx-3"
        :message="errorText(discussions.error, 'Could not load discussions.')"
        @retry="retryLoad"
      />
      <EmptyStateBox
        class="mx-3"
        v-else-if="!discussions.loading && discussions.data && isEmpty"
        v-bind="emptyState"
      />
      <div class="flex items-center justify-center p-3" v-if="showLoadMoreButton">
        <Button label="Load more" :loading="discussions.loading" @click="discussions.next" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, toValue } from 'vue'
import { toast, type OrderBy } from 'frappe-ui'
import { List } from 'frappe-ui/list'
import { type Discussion, UseDiscussionOptions, useDiscussions } from '@/data/discussions'
import { removeBookmark, restoreBookmark } from '@/data/bookmarks'
import { errorText } from '@/utils'
import LoadError from './LoadError.vue'
import DiscussionRow from './DiscussionRow.vue'
import ListRowSkeleton from './ListRowSkeleton.vue'
import EmptyStateBox, { type EmptyState } from './EmptyStateBox.vue'
import { feedEmptyStates } from '@/data/discussionFeeds'

interface Props {
  filters: UseDiscussionOptions['filters']
  orderBy?: UseDiscussionOptions['orderBy']
  cacheKey?: string
  showPinned?: boolean
  selectable?: boolean
  // Name each row's community too, for lists that mix communities. A space name
  // alone is ambiguous there.
  showCommunity?: boolean
  emptyState?: EmptyState
  // Bookmark rows get a hover button that removes the bookmark, with Undo.
  removableBookmarks?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showPinned: true,
  selectable: false,
  showCommunity: false,
  removableBookmarks: false,
  emptyState: () => feedEmptyStates.recent,
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
const showLoadMoreButton = computed(() => discussions.hasNextPage && !isEmpty.value)
const isSortedByCreation = computed(() => toValue(props.orderBy) === 'creation desc')

// Held back until the first page arrives, so they do not sit above the skeleton rows.
const visiblePinnedDiscussions = computed(() =>
  isInitialLoading.value ? [] : pinnedDiscussions.data || [],
)
const pinnedNames = computed(() => new Set(visiblePinnedDiscussions.value.map((d) => d.name)))
const isEmpty = computed(
  () => visiblePinnedDiscussions.value.length === 0 && visibleDiscussions.value.length === 0,
)

// Rows removed here hide at once; the list reloads once the server agrees. A pinned
// discussion already leads the list, so it is not shown again in its date position.
const removedRowKeys = ref(new Set<string>())
const visibleDiscussions = computed(() =>
  (discussions.data || []).filter(
    (discussion) =>
      !removedRowKeys.value.has(rowKey(discussion)) && !pinnedNames.value.has(discussion.name),
  ),
)

// The pinned list fails with the main one on a failed first load, so retry both.
function retryLoad() {
  discussions.reload()
  if (props.showPinned) pinnedDiscussions.reload()
}

function rowKey(discussion: Discussion) {
  return discussion.bookmark || discussion.name
}

function removeBookmarkRow(discussion: Discussion) {
  const key = rowKey(discussion)
  setRowRemoved(key, true)
  removeBookmark(discussion)
    .then(() => {
      discussions.reload()
      toast.success('Bookmark removed', {
        action: { label: 'Undo', onClick: () => undoRemoveBookmark(discussion, key) },
      })
    })
    .catch((error: unknown) => {
      setRowRemoved(key, false)
      toast.error(errorText(error, 'Could not remove the bookmark.'))
    })
}

function undoRemoveBookmark(discussion: Discussion, key: string) {
  restoreBookmark(discussion)
    .then(() => {
      setRowRemoved(key, false)
      discussions.reload()
    })
    .catch((error: unknown) => toast.error(errorText(error, 'Could not restore the bookmark.')))
}

function setRowRemoved(key: string, removed: boolean) {
  const keys = new Set(removedRowKeys.value)
  if (removed) keys.add(key)
  else keys.delete(key)
  removedRowKeys.value = keys
}

defineExpose({ discussions, pinnedDiscussions })
</script>
