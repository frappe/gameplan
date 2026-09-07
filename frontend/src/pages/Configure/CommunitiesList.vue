<template>
  <CommunitiesListFilters
    v-if="showControls"
    v-model:search="search"
    v-model:visibility-filter="visibilityFilter"
  />

  <ConfigureEmptyState
    v-if="!visibleCommunities.length"
    icon="lucide-blocks"
    title="No communities yet"
    :description="
      showCreateCommunity
        ? 'Create a community to group related spaces, members, and discussions.'
        : 'A Gameplan Admin creates communities. Ask for one, or for an invite to a private community.'
    "
  >
    <template #actions>
      <Button
        v-if="showCreateCommunity"
        icon-left="lucide-plus"
        variant="solid"
        @click="emit('create-community')"
      >
        New community
      </Button>
    </template>
  </ConfigureEmptyState>

  <List
    v-else-if="filteredCommunities.length"
    :columns="['minmax(12rem,6fr)', 'minmax(6rem,1.2fr)', 'minmax(6rem,1.2fr)', '5.75rem']"
    class="list-gap-12 max-md:list-cols-[minmax(0,1fr)]"
  >
    <!-- Sticky at the settings scroll-viewport top — it rests exactly where it
         pins, so it never visibly moves. px-1.5 aligns the labels with the
         ghost-button text in the rows below. -->
    <ListHeader class="sticky top-0 z-10 bg-surface-elevation-1 max-md:hidden">
      <ListHeaderCell>Community</ListHeaderCell>
      <ListHeaderCell class="px-1.5">Spaces</ListHeaderCell>
      <ListHeaderCell class="px-1.5">Members</ListHeaderCell>
      <!-- Join/Leave and the options button share the last column so both hug
           the right edge. It is 5.75rem: the 4rem membership button, the gap,
           and the 1.5rem options button. Anything narrower spills left over the
           members column. -->
      <ListHeaderCell />
    </ListHeader>
    <CommunityRow
      v-for="community in filteredCommunities"
      :key="community.name"
      :community="community"
      :spaces-count="getActiveCommunitySpacesCount(community.name)"
      @view-spaces="emit('view-spaces', community.name)"
      @view-members="emit('view-members', community.name)"
      @merged="emit('community-merged', $event)"
    />
  </List>

  <ConfigureEmptyState
    v-else
    icon="lucide-search-x"
    title="No communities match these filters"
    description="Clear the current filters to see every community."
    class="mt-4"
  >
    <template #actions>
      <Button @click="clearFilters">Clear filters</Button>
    </template>
  </ConfigureEmptyState>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Button } from 'frappe-ui'
import { List, ListHeader, ListHeaderCell } from 'frappe-ui/list'
import { communities, type Community } from '@/data/communities'
import { spaces } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { isGlobalAdmin } from '@/utils/permissions'
import ConfigureEmptyState from './ConfigureEmptyState.vue'
import CommunityRow from './CommunityRow.vue'
import CommunitiesListFilters from './CommunitiesListFilters.vue'

type VisibilityFilter = 'All' | 'Public' | 'Private' | 'Archived'

// Filters are models so a parent (e.g. the Settings dialog) can hoist the
// controls into a fixed header while this component still renders the list.
const search = defineModel<string>('search', { default: '' })
const visibilityFilter = defineModel<VisibilityFilter>('visibilityFilter', { default: 'All' })
const sessionUser = useSessionUser()
withDefaults(
  defineProps<{
    // When false, the parent owns the filter controls; we only render the list.
    showControls?: boolean
  }>(),
  {
    showControls: true,
  },
)
const emit = defineEmits<{
  (event: 'create-community'): void
  (event: 'view-spaces', communityId: string): void
  (event: 'view-members', communityId: string): void
  (event: 'community-merged', communityId: string): void
}>()

const filteredCommunities = computed(() => {
  const term = search.value.trim().toLowerCase()
  return visibleCommunities.value.filter(
    (community) =>
      matchesScope(community, visibilityFilter.value) &&
      (!term || community.title.toLowerCase().includes(term)),
  )
})

// Every community the user can read — public ones plus the private ones they belong
// to; the backend list query scopes it. Members browse the full list to find one to
// join, and each row only offers the actions that user can take.
const visibleCommunities = computed(() => communities.data || [])
const hasArchivedCommunities = computed(() =>
  visibleCommunities.value.some((community) => community.archived_at),
)
const showCreateCommunity = computed(() => isGlobalAdmin(sessionUser))

// If the archived scope empties out, fall back to the default scope.
watch(hasArchivedCommunities, (value) => {
  if (!value && visibilityFilter.value === 'Archived') {
    visibilityFilter.value = 'All'
  }
})

// 'All'/'Public'/'Private' only cover active communities; 'Archived' is its own scope.
function matchesScope(community: Community, filter: VisibilityFilter) {
  if (filter === 'Archived') return Boolean(community.archived_at)
  if (community.archived_at) return false
  if (filter === 'Public') return !community.is_private
  if (filter === 'Private') return Boolean(community.is_private)
  return true
}

function getActiveCommunitySpacesCount(communityId: string) {
  return (spaces.data || []).filter((space) => {
    return space.team === communityId && !space.archived_at
  }).length
}

function clearFilters() {
  visibilityFilter.value = 'All'
  search.value = ''
}
</script>
