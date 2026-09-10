<template>
  <CommunitySpacesListControls
    v-if="showControls"
    :community-id="communityId"
    v-model:search="search"
    v-model:visibility-filter="visibilityFilter"
  />

  <List
    v-if="filteredSpaces.length"
    :columns="{
      base: ['minmax(0,1fr)', 'auto'],
      md: hasGuests
        ? ['minmax(8rem,1fr)', '15.25rem', '5rem', '1.5rem']
        : ['minmax(8rem,1fr)', '15.25rem', '1.5rem'],
    }"
    class="list-gap-12 max-md:list-gap-1"
  >
    <!-- Sticky at the settings scroll-viewport top — it rests exactly where it
         pins, so it never visibly moves. -->
    <ListHeader class="sticky top-0 z-10 bg-surface-elevation-1 max-md:hidden">
      <ListHeaderCell>Space</ListHeaderCell>
      <ListHeaderCell>Content</ListHeaderCell>
      <ListHeaderCell v-if="hasGuests">Guests</ListHeaderCell>
      <ListHeaderCell />
    </ListHeader>
    <SpaceRow
      v-for="space in filteredSpaces"
      :key="space.name"
      :space="space"
      :pages-count="getPagesCount(space.name)"
      :guests-count="getGuestsCount(space.name)"
      :show-guests="hasGuests"
    />
  </List>

  <ConfigureEmptyState
    v-else-if="!communitySpaces.length"
    icon="lucide-panels-top-left"
    title="No spaces yet"
    description="Create the first space for discussions, pages, and tasks in this community."
  >
    <template #actions>
      <Button
        v-if="canCreateSpace"
        icon-left="lucide-plus"
        variant="solid"
        @click="emit('create-space')"
      >
        New space
      </Button>
    </template>
  </ConfigureEmptyState>

  <ConfigureEmptyState
    v-else
    icon="lucide-search-x"
    title="No spaces match these filters"
    description="Clear the current filters to see every space in this community."
  >
    <template #actions>
      <Button @click="clearFilters">Clear filters</Button>
    </template>
  </ConfigureEmptyState>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import { List, ListHeader, ListHeaderCell } from 'frappe-ui/list'
import type { Space } from '@/data/spaces'
import ConfigureEmptyState from './ConfigureEmptyState.vue'
import SpaceRow from './SpaceRow.vue'
import CommunitySpacesListControls from './CommunitySpacesListControls.vue'
import { useCommunitySpaceData } from './useCommunitySpaceData'
import { computed } from 'vue'

type VisibilityFilter = 'All' | 'Public' | 'Private' | 'Archived'

const props = withDefaults(
  defineProps<{
    communityId: string
    canCreateSpace: boolean
    // When false, the parent owns the filter controls; we only render the list.
    showControls?: boolean
  }>(),
  {
    showControls: true,
  },
)
const emit = defineEmits<{
  (event: 'create-space'): void
}>()

// Filters are models so the Settings dialog can hoist the controls into its
// fixed header while this component still renders the list.
const search = defineModel<string>('search', { default: '' })
const visibilityFilter = defineModel<VisibilityFilter>('visibilityFilter', { default: 'All' })

const { communitySpaces, getPagesCount, getGuestsCount, hasGuests } = useCommunitySpaceData(
  () => props.communityId,
)

const filteredSpaces = computed(() => {
  const term = search.value.trim().toLowerCase()
  return communitySpaces.value.filter(
    (space) =>
      matchesScope(space, visibilityFilter.value) &&
      (!term || space.title.toLowerCase().includes(term)),
  )
})

// 'All'/'Public'/'Private' only cover active spaces; 'Archived' is its own scope.
function matchesScope(space: Space, filter: VisibilityFilter) {
  if (filter === 'Archived') return Boolean(space.archived_at)
  if (space.archived_at) return false
  if (filter === 'Public') return !space.is_private
  if (filter === 'Private') return Boolean(space.is_private)
  return true
}

function clearFilters() {
  visibilityFilter.value = 'All'
  search.value = ''
}
</script>
