<template>
  <div>
    <div>
      <PageHeaderMobile class="sm:hidden" title="Search" />
      <PageHeader class="hidden sm:flex">
        <Breadcrumbs :items="[{ label: 'Search', route: { name: 'Search' } }]" />
      </PageHeader>
      <div class="body-container">
        <!-- Sticky search + filter toolbar; results scroll beneath it. Bled out
             by the body-container padding so the background covers the gutters. -->
        <div class="sticky top-0 z-10 -mx-3 bg-surface-base px-3 pt-5 sm:-mx-5 sm:px-5 sm:pt-6">
          <div class="flex items-center space-x-2">
            <TextInput
              ref="searchInput"
              class="flex-1"
              placeholder="Search or press / to focus"
              v-focus
              :model-value="query"
              @update:model-value="updateQuery"
              @keydown="newSearch = true"
              @keydown.enter="() => submit()"
            >
              <template #prefix>
                <span class="lucide-search w-4 text-ink-gray-5" />
              </template>
              <template #suffix>
                <div class="flex items-center">
                  <button
                    v-if="query"
                    @click="clearSearch"
                    aria-label="Clear search"
                    class="p-1 size-6 grid place-content-center focus:outline-none focus:ring focus:ring-outline-gray-3 rounded-4"
                  >
                    <span class="lucide-x w-4 text-ink-gray-7" />
                  </button>
                </div>
              </template>
            </TextInput>
          </div>

          <!-- Filter Panel -->
          <div class="overflow-x-auto -mx-3 px-3 pt-2">
            <div class="flex gap-2 items-center">
              <!-- Authors Filter -->
              <MultiSelect
                :options="authorsFilterOptions"
                :model-value="activeFilters.owner || []"
                @update:model-value="(values) => updateFilter('owner', values)"
                placeholder="Author"
              >
                <template #trigger="{ open, selectedOptions, toggleOpen }">
                  <Button variant="outline" @click="toggleOpen">
                    <div
                      class="flex min-h-[20px] items-center"
                      :class="{ 'gap-2': selectedOptions.length > 0 }"
                    >
                      <template v-if="selectedOptions.length > 0">
                        <div class="isolate flex -space-x-2">
                          <Avatar
                            v-for="(opt, i) in selectedOptions.slice(0, 3)"
                            :key="opt.value"
                            :image="opt.image"
                            :label="opt.label"
                            class="border-2 border-white flex-shrink-0"
                            size="xs"
                            :style="{ zIndex: 10 - i }"
                          />
                        </div>
                        <span class="text-ink-gray-7">
                          {{
                            selectedOptions.length === 1
                              ? selectedOptions[0].label
                              : `${selectedOptions.length} users`
                          }}
                        </span>
                      </template>
                      <span v-else class="text-ink-gray-4">Author</span>
                    </div>
                    <template #suffix>
                      <span
                        class="lucide-chevron-down ml-2 h-4 w-4 transition-transform"
                        :class="{ 'rotate-180': open }"
                      />
                    </template>
                  </Button>
                </template>
                <template #item-prefix="{ item }">
                  <Avatar :image="item.image" :label="item.label" size="xs" />
                </template>
                <template #item-suffix="{ item }">
                  <span v-if="(item.count ?? 0) > 0" class="text-xs text-ink-gray-5">{{
                    item.count
                  }}</span>
                </template>
              </MultiSelect>

              <!-- Projects Filter -->
              <MultiSelect
                variant="outline"
                :options="spacesFilterOptions"
                :model-value="activeFilters.project || []"
                @update:model-value="(values) => updateFilter('project', values)"
                placeholder="Space"
              >
                <template #item-suffix="{ item }">
                  <span v-if="(item.count ?? 0) > 0" class="text-xs text-ink-gray-5">{{
                    item.count
                  }}</span>
                </template>
              </MultiSelect>

              <!-- Teams Filter -->
              <MultiSelect
                variant="outline"
                :options="teamsFilterOptions"
                :model-value="activeFilters.team || []"
                @update:model-value="(values) => updateFilter('team', values)"
                placeholder="Community"
              >
                <template #item-suffix="{ item }">
                  <span v-if="(item.count ?? 0) > 0" class="text-xs text-ink-gray-5">{{
                    item.count
                  }}</span>
                </template>
              </MultiSelect>

              <!-- Document Type Filter -->
              <MultiSelect
                variant="outline"
                :options="doctypesFilterOptions"
                :model-value="activeFilters.doctype || []"
                @update:model-value="(values) => updateFilter('doctype', values)"
                placeholder="Type"
              >
                <template #item-suffix="{ item }">
                  <span v-if="(item.count ?? 0) > 0" class="text-xs text-ink-gray-5">{{
                    item.count
                  }}</span>
                </template>
              </MultiSelect>

              <!-- Tags Filter -->
              <MultiSelect
                variant="outline"
                :options="tagsFilterOptions"
                :model-value="activeFilters.tags || []"
                @update:model-value="(values) => updateFilter('tags', values)"
                placeholder="Tags"
              >
                <template #item-suffix="{ item }">
                  <span v-if="(item.count ?? 0) > 0" class="text-xs text-ink-gray-5">{{
                    item.count
                  }}</span>
                </template>
              </MultiSelect>
            </div>
          </div>
          <!-- Soft fade so results dissolve into the toolbar as they scroll under. -->
          <div
            class="pointer-events-none absolute inset-x-0 top-full h-6 bg-gradient-to-b from-surface-base/90 to-transparent"
          />
        </div>

        <!-- Search Summary -->
        <div class="mt-2 text-sm flex items-center justify-between min-h-6">
          <div>
            <template v-if="search.error">
              <ErrorMessage
                :message="
                  search.error.type == 'GameplanSearchIndexMissingError'
                    ? 'Search index does not exist. Please build the index first.'
                    : search.error
                "
              />
            </template>
            <template v-else-if="newSearch && query.length > 3">
              <p class="text-ink-gray-6">Press enter to search</p>
            </template>
            <template v-else-if="search.loading">
              <p class="text-ink-gray-6">Searching...</p>
            </template>
            <template v-else-if="searchResponse?.summary">
              <div class="space-y-1">
                <p class="text-ink-gray-6">
                  {{ visibleSearchResults.length }}
                  {{ visibleSearchResults.length === 1 ? 'match' : 'matches' }} ({{
                    searchResponse.summary.duration
                  }}s)
                  <span v-if="hasActiveFilters()">
                    •
                    {{ Object.keys(searchResponse.summary.applied_filters || {}).length }} filter(s)
                    applied
                  </span>
                </p>
                <p v-if="searchResponse.summary.corrected_query" class="text-ink-gray-6">
                  <span class="text-ink-gray-5">Searched for:</span>
                  <span class="ml-1 font-medium text-primary">
                    {{ searchResponse.summary.corrected_query }}
                  </span>
                </p>
              </div>
            </template>
          </div>

          <!-- Inline Feedback Section -->
          <div v-if="visibleSearchResults.length && !feedbackGiven" class="flex items-center gap-2">
            <span class="text-ink-gray-6">Helpful?</span>
            <div class="flex items-center gap-1">
              <Tooltip text="Yes, results were helpful">
                <button
                  @click="submitFeedback(true)"
                  class="p-1 hover:bg-surface-gray-2 rounded-full transition-colors"
                >
                  <span class="lucide-thumbs-up size-4 text-ink-gray-7" />
                </button>
              </Tooltip>
              <Tooltip text="No, results were not helpful">
                <button
                  @click="submitFeedback(false)"
                  class="p-1 hover:bg-surface-gray-2 rounded-full transition-colors"
                >
                  <span class="lucide-thumbs-down size-4 text-ink-gray-7" />
                </button>
              </Tooltip>
            </div>
          </div>
          <div v-else-if="feedbackGiven" class="text-ink-gray-6">Thanks for your feedback!</div>
        </div>

        <div class="mt-5 -mx-2.5 pb-20">
          <List :columns="['auto', 'minmax(0,1fr)']" class="list-row-px-2.5" divider="inset">
            <ListRow
              v-for="item in visibleSearchResults"
              :key="item.id"
              :to="getItemRoute(item)"
              class="py-3 touch-pan-y overflow-hidden"
            >
              <ListCell class="self-start">
                <UserAvatarWithHover :user="item.author" />
              </ListCell>
              <ListCell class="self-start">
                <div class="w-full">
                  <div class="flex items-center">
                    <div
                      v-if="item.title"
                      class="text-base-medium text-ink-gray-9"
                      v-html="item.title"
                    />
                    <div class="text-base-medium text-ink-gray-9" v-else>
                      {{ $user(item.author).full_name }}
                    </div>
                    <span class="px-1 leading-none text-sm text-ink-gray-5">
                      &middot; {{ item.doctype.replace('GP ', '') }}
                    </span>
                    <div class="ml-auto text-sm text-ink-gray-5">
                      {{ dayjs.unix(item.modified).format('lll') }}
                    </div>
                  </div>
                  <div
                    v-if="item.content"
                    class="mt-1 text-p-base text-ink-gray-6"
                    v-html="item.content"
                  ></div>
                </div>
              </ListCell>
            </ListRow>
          </List>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, useTemplateRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  PageHeader,
  PageHeaderMobile,
  Avatar,
  Breadcrumbs,
  Button,
  MultiSelect,
  TextInput,
  Tooltip,
  dayjs,
  debounce,
  usePageMeta,
} from 'frappe-ui'
import { useCall, useNewDoc } from 'frappe-ui'
import { List, ListCell, ListRow } from 'frappe-ui/list'
import { GPSearchFeedback } from '@/types/doctypes'
import { useSessionUser } from '@/data/users'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { getSpace } from '@/data/spaces'
import { activeCommunities } from '@/data/communities'
import { activeUsers } from '@/data/users'
import { vFocus } from '@/directives'

// Type Definitions
interface SearchSummary {
  duration: number
  total_matches: number
  returned_matches: number
  filtered_matches: number
  corrected_words?: Record<string, string>
  corrected_query?: string
  applied_filters?: SearchFilters
}

interface SearchResultItem {
  id: string
  title: string
  content: string
  preview: string
  doctype: string
  name: string
  project: string
  team?: string
  reference_doctype: string
  reference_name: string
  modified: number
  author: string
  score: number
}

interface SearchResponse {
  results: SearchResultItem[]
  summary: SearchSummary
}

interface SearchParams {
  query: string
  filters?: string
}

interface SearchFilters {
  owner?: string[]
  project?: string[]
  team?: string[]
  doctype?: string[]
  tags?: string[]
}

interface FilterOption {
  value: string
  label: string
  count?: number
  image?: string
}

interface FilterOptions {
  authors: Record<string, number>
  projects: Record<string, number>
  teams: Record<string, number>
  doctypes: Record<string, number>
  tags: Record<string, number>
}

// Constants and Configuration
const STORAGE_KEY_PREFIX = 'gameplan_search:'

// Reactive State
const query = ref('')
const searchResponse = ref<SearchResponse | null>(null)
const newSearch = ref(true)
const feedbackGiven = ref(false)
const activeFilters = ref<SearchFilters>({})

// Template Refs
const searchInput = useTemplateRef<typeof TextInput>('searchInput')

// Composables and External Data
const router = useRouter()
const route = useRoute()
const groupedSpaces = useGroupedSpaceOptions()
const visibleSearchResults = computed(() => {
  return (searchResponse.value?.results || []).filter(isSearchResultVisible)
})

// API Calls Setup
const search = useCall<SearchResponse, SearchParams>({
  url: '/api/v2/method/gameplan.api.search_sqlite',
  immediate: false,
  onSuccess(response) {
    searchResponse.value = response
    if (query.value) {
      saveSearchState(query.value, response)
    }
  },
})

const filterOptions = useCall<FilterOptions>({
  url: '/api/v2/method/gameplan.api.get_search_filter_options',
  immediate: true,
  initialData: {
    authors: {},
    projects: {},
    teams: {},
    doctypes: {},
    tags: {},
  },
})

// Computed Properties for Filter Options
const spacesFilterOptions = computed(() => {
  // Convert the projects dict from API to a Map for lookups
  const projectCounts = new Map()
  if (filterOptions.data?.projects) {
    Object.entries(filterOptions.data.projects).forEach(([projectName, count]) => {
      projectCounts.set(projectName, count)
      // Project IDs are looked up numerically elsewhere; add a numeric key only
      // when the name actually parses (Number() returns NaN, it never throws).
      const numericKey = Number(projectName)
      if (!Number.isNaN(numericKey)) {
        projectCounts.set(numericKey, count)
      }
    })
  }

  // Handle both flat and grouped space options
  const spaces = groupedSpaces.value
  if (!spaces || spaces.length === 0) {
    return []
  }

  const firstItem = spaces[0]

  // Check if it's grouped (has 'group' property) or flat (has 'label' property)
  if (firstItem && 'group' in firstItem) {
    // It's grouped - transform each group
    return spaces.map((group: any) => ({
      ...group,
      options: group.options.map((space: any) => ({
        ...space,
        count: projectCounts.get(space.value) || projectCounts.get(Number(space.value)) || 0,
      })),
    }))
  } else if (firstItem && 'label' in firstItem) {
    // It's flat - transform directly
    return spaces.map((space: any) => ({
      ...space,
      count: projectCounts.get(space.value) || projectCounts.get(Number(space.value)) || 0,
    }))
  }

  return []
})

const teamsFilterOptions = computed(() => {
  // Convert the teams dict from API to a Map for lookups
  const teamCounts = new Map()
  if (filterOptions.data?.teams) {
    Object.entries(filterOptions.data.teams).forEach(([teamName, count]) => {
      teamCounts.set(teamName, count)
    })
  }

  return activeCommunities.value.map((community) => ({
    value: community.name,
    label: community.title,
    count: teamCounts.get(community.name) || 0,
  }))
})

const authorsFilterOptions = computed(() => {
  // Convert the authors dict from API to a Map for lookups
  const authorCounts = new Map()
  if (filterOptions.data?.authors) {
    Object.entries(filterOptions.data.authors).forEach(([authorName, count]) => {
      authorCounts.set(authorName, count)
    })
  }

  return activeUsers.value.map((user) => ({
    value: user.name,
    label: user.full_name,
    image: user.user_image,
    count: authorCounts.get(user.name) || 0,
  }))
})

const doctypesFilterOptions = computed(() => {
  // Convert the doctypes dict from API to a Map for lookups
  const doctypeCounts = new Map()
  if (filterOptions.data?.doctypes) {
    Object.entries(filterOptions.data.doctypes).forEach(([doctypeName, count]) => {
      doctypeCounts.set(doctypeName, count)
    })
  }

  // Static mapping of doctypes with their display labels
  const doctypeMapping = [
    { value: 'GP Discussion', label: 'Discussion' },
    { value: 'GP Task', label: 'Task' },
    { value: 'GP Page', label: 'Page' },
    { value: 'GP Comment', label: 'Comment' },
  ]

  return doctypeMapping.map((doctype) => ({
    value: doctype.value,
    label: doctype.label,
    count: doctypeCounts.get(doctype.value) || 0,
  }))
})

const tagsFilterOptions = computed(() => {
  // Convert the tags dict from API to filter options
  if (!filterOptions.data?.tags) {
    return []
  }

  return Object.entries(filterOptions.data.tags)
    .map(([tagName, count]) => ({
      value: tagName,
      label: tagName,
      count: count,
    }))
    .sort((a, b) => b.count - a.count) // Sort by count descending
})

// Keyboard shortcut handler
function handleKeyPress(event: KeyboardEvent) {
  if (isInputFocused()) {
    return
  }

  if (event.key === '/') {
    event.preventDefault()
    focusSearchInput()
    return
  }

  if (!isSearchCharacter(event)) {
    return
  }

  event.preventDefault()
  focusSearchInput()
  newSearch.value = true
  updateQuery(`${query.value}${event.key}`)
}

function focusSearchInput() {
  searchInput.value?.el?.focus()
}

function isSearchCharacter(event: KeyboardEvent) {
  return (
    event.key.length === 1 && event.key !== ' ' && !event.ctrlKey && !event.metaKey && !event.altKey
  )
}

function isInputFocused() {
  const activeElement = document.activeElement
  return (
    activeElement?.tagName === 'INPUT' ||
    activeElement?.tagName === 'TEXTAREA' ||
    (activeElement as HTMLElement)?.contentEditable === 'true'
  )
}

// Lifecycle Hooks
onMounted(() => {
  const searchQuery = route.query.q as string
  if (searchQuery) {
    query.value = searchQuery
    if (!loadSearchState(searchQuery)) {
      submit()
    }
  } else {
    clearStoredSearches()
  }
  // Add global keyboard shortcut listener
  document.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  // Clean up event listener
  document.removeEventListener('keydown', handleKeyPress)
})

// Page Meta Configuration
usePageMeta(() => {
  return {
    title: 'Search',
  }
})

// Search and Query Management
function updateQuery(value: string) {
  query.value = value
  router.replace({ query: value ? { q: value } : {} })
}

const submit = debounce(function (text?: string) {
  newSearch.value = false
  feedbackGiven.value = false
  if (text !== undefined) {
    query.value = text
  }

  const searchQuery = text || query.value
  router.replace({ query: searchQuery ? { q: searchQuery } : {} })

  const params: SearchParams = { query: searchQuery }

  // Add filters if any are active
  if (hasActiveFilters()) {
    params.filters = JSON.stringify(activeFilters.value)
  }

  search.submit(params)
}, 300)

function clearSearch() {
  query.value = ''
  searchResponse.value = null
  newSearch.value = true
  feedbackGiven.value = false
  clearStoredSearches()
  router.replace({ query: {} })
}

// Filter Management
function hasActiveFilters(): boolean {
  return Object.values(activeFilters.value).some((filter) =>
    Array.isArray(filter) ? filter.length > 0 : Boolean(filter),
  )
}

function updateFilter(type: keyof SearchFilters, values: string[]) {
  if (values.length === 0) {
    delete activeFilters.value[type]
  } else {
    activeFilters.value[type] = values
  }
  submit()
}

function addFilter(type: keyof SearchFilters, value: string) {
  if (!activeFilters.value[type]) {
    activeFilters.value[type] = []
  }
  const currentFilter = activeFilters.value[type] as string[]
  if (!currentFilter.includes(value)) {
    currentFilter.push(value)
    submit()
  }
}

function removeFilter(type: keyof SearchFilters, value: string) {
  const currentFilter = activeFilters.value[type] as string[]
  if (currentFilter) {
    const index = currentFilter.indexOf(value)
    if (index > -1) {
      currentFilter.splice(index, 1)
      if (currentFilter.length === 0) {
        delete activeFilters.value[type]
      }
      submit()
    }
  }
}

// Search State Persistence
function getStorageKey(query: string) {
  return `${STORAGE_KEY_PREFIX}${useSessionUser().name}:${query}`
}

function loadSearchState(searchQuery: string) {
  const saved = localStorage.getItem(getStorageKey(searchQuery))
  if (saved) {
    const state = JSON.parse(saved)
    // Check if stored result is less than 30 minutes old
    if (Date.now() - state.timestamp < 30 * 60 * 1000) {
      searchResponse.value = state.results
      // Restore active filters if they exist
      if (state.filters) {
        activeFilters.value = state.filters
      }
      newSearch.value = false
      return true
    }
    // Remove expired results
    localStorage.removeItem(getStorageKey(searchQuery))
  }
  return false
}

function saveSearchState(searchQuery: string, results: SearchResponse) {
  const state = {
    results,
    filters: activeFilters.value,
    timestamp: Date.now(),
  }
  localStorage.setItem(getStorageKey(searchQuery), JSON.stringify(state))
}

function clearStoredSearches() {
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(STORAGE_KEY_PREFIX)) {
      localStorage.removeItem(key)
    }
  }
}

// Navigation and Routing
function getItemRoute(item: SearchResultItem) {
  switch (item.doctype) {
    case 'GP Discussion':
      return {
        name: 'Discussion',
        params: {
          communityId: item.team || getSpace(item.project)?.team,
          spaceId: item.project,
          postId: item.name,
        },
        query: {
          comment: 'first_post',
        },
      }
    case 'GP Task':
      return {
        name: 'SpaceTask',
        params: {
          communityId: item.team || getSpace(item.project)?.team,
          spaceId: item.project,
          taskId: item.name,
        },
      }
    case 'GP Page':
      return {
        name: 'SpacePage',
        params: {
          communityId: item.team || getSpace(item.project)?.team,
          spaceId: item.project,
          pageId: item.name,
        },
      }
    case 'GP Comment':
      if (item.reference_doctype === 'GP Discussion') {
        return {
          name: 'Discussion',
          params: {
            communityId: item.team || getSpace(item.project)?.team,
            spaceId: item.project,
            postId: item.reference_name,
          },
          query: { comment: item.name },
        }
      }
      if (item.reference_doctype === 'GP Task') {
        return {
          name: 'SpaceTask',
          params: {
            communityId: item.team || getSpace(item.project)?.team,
            spaceId: item.project,
            taskId: item.reference_name,
          },
          query: { comment: item.name },
        }
      }
      return {}
    default:
      return {}
  }
}

function isSearchResultVisible(item: SearchResultItem) {
  if (!item.project) return true

  // Search spans every community the user can access, joined or not — the backend
  // already filters results by permission. Only hide results from archived spaces;
  // if the space isn't in the local cache, still show it (the server allowed it).
  const space = getSpace(item.project)
  return !space || !space.archived_at
}

// Feedback System
function submitFeedback(isHelpful: boolean) {
  let feedback = useNewDoc<GPSearchFeedback>('GP Search Feedback', {
    helpful: isHelpful ? 'Yes' : 'No',
    user: useSessionUser().name,
    query: query.value,
  })

  feedback.submit().then(() => {
    feedbackGiven.value = true
  })
}
</script>
<style>
mark {
  background-color: var(--surface-amber-2);
  color: var(--ink-gray-8);
  font-weight: 500;
}
</style>
