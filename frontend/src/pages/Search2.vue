<template>
  <div>
    <div>
      <header class="sticky top-0 z-10 border-b bg-surface-white px-4 py-2.5 sm:px-5">
        <div class="flex items-center justify-between">
          <Breadcrumbs :items="[{ label: 'Search', route: { name: 'Search' } }]" />
        </div>
      </header>
      <div class="mx-auto mt-6 max-w-4xl px-4 sm:px-5">
        <div class="flex items-center space-x-2 px-2.5">
          <TextInput
            class="flex-1"
            placeholder="Search"
            autocomplete="off"
            :model-value="query"
            @update:model-value="updateQuery"
            @keydown="newSearch = true"
            @keydown.enter="(e) => submit(e.target.value)"
          >
            <template #prefix>
              <LucideSearch class="w-4 text-ink-gray-5" />
            </template>
            <template #suffix>
              <div class="flex items-center">
                <button
                  v-if="query"
                  @click="clearSearch"
                  class="p-1 size-6 grid place-content-center focus:outline-none focus:ring focus:ring-outline-gray-3 rounded"
                >
                  <LucideX class="w-4 text-ink-gray-7" />
                </button>
              </div>
            </template>
          </TextInput>
        </div>

        <!-- Search Summary -->
        <div class="mt-2 px-2.5 text-sm flex items-center justify-between min-h-6">
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
              <p class="text-ink-gray-6">
                Showing {{ searchResponse.summary.filtered_matches }} out of
                {{ searchResponse.summary.total_matches }} matches ({{
                  searchResponse.summary.duration
                }}s)
              </p>
              <p v-if="searchResponse.summary.corrected_words" class="mt-1">
                <span class="text-ink-gray-5">Searched for:</span>
                <span
                  v-for="(corrected, original) in searchResponse.summary.corrected_words"
                  :key="original"
                  class="ml-1 font-medium text-primary"
                >
                  {{ corrected }}
                </span>
              </p>
            </template>
          </div>

          <!-- Inline Feedback Section -->
          <div
            v-if="searchResponse?.results?.length && !feedbackGiven"
            class="flex items-center gap-2"
          >
            <span class="text-ink-gray-6">Helpful?</span>
            <div class="flex items-center gap-1">
              <Tooltip text="Yes, results were helpful">
                <button
                  @click="submitFeedback(true)"
                  class="p-1 hover:bg-surface-gray-2 rounded-full transition-colors"
                >
                  <LucideThumbsUp class="size-4 text-ink-gray-7" />
                </button>
              </Tooltip>
              <Tooltip text="No, results were not helpful">
                <button
                  @click="submitFeedback(false)"
                  class="p-1 hover:bg-surface-gray-2 rounded-full transition-colors"
                >
                  <LucideThumbsDown class="size-4 text-ink-gray-7" />
                </button>
              </Tooltip>
            </div>
          </div>
          <div v-else-if="feedbackGiven" class="text-ink-gray-6">Thanks for your feedback!</div>
        </div>

        <div class="mt-5">
          <template v-for="item in searchResponse?.results" :key="item.id">
            <router-link
              :to="getItemRoute(item)"
              class="flex space-x-2 overflow-hidden rounded px-2.5 py-3 hover:bg-surface-gray-2"
            >
              <div>
                <UserAvatarWithHover :user="item.author" />
              </div>
              <div class="w-full">
                <div class="flex items-center">
                  <div v-if="item.title" class="text-base font-medium" v-html="item.title" />
                  <div class="text-base font-medium" v-else>
                    {{ $user(item.author).full_name }}
                  </div>
                  <span class="px-1 leading-none text-sm text-ink-gray-5">
                    &middot; {{ item.doctype.replace('GP ', '') }}
                  </span>
                  <div class="ml-auto text-sm text-ink-gray-5">
                    {{ $dayjs.unix(item.timestamp).format('lll') }}
                  </div>
                </div>
                <div
                  v-if="item.content"
                  class="mt-1 text-p-base text-ink-gray-6"
                  v-html="item.content"
                ></div>
              </div>
            </router-link>
            <div class="border-b mx-2"></div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Breadcrumbs, TextInput, debounce, usePageMeta, Tooltip } from 'frappe-ui'
import { useCall, useNewDoc } from 'frappe-ui/src/data-fetching'
import LucideX from '~icons/lucide/x'
import LucideThumbsUp from '~icons/lucide/thumbs-up'
import LucideThumbsDown from '~icons/lucide/thumbs-down'
import { GPSearchFeedback } from '@/types/doctypes'
import { useSessionUser } from '@/data/users'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'

interface SearchSummary {
  duration: number
  total_matches: number
  returned_matches: number
  filtered_matches: number
  corrected_words?: Record<string, string>
}

interface SearchResultItem {
  id: string
  title: string
  content: string
  preview: string
  doctype: string
  name: string
  project: string
  reference_doctype: string
  reference_name: string
  timestamp: number
  author: string
  score: number
}

interface SearchResponse {
  results: SearchResultItem[]
  summary: SearchSummary
}

interface SearchParams {
  query: string
}

// Constants
const STORAGE_KEY_PREFIX = 'gameplan_search:'

// Get storage key for specific query
function getStorageKey(query: string) {
  return `${STORAGE_KEY_PREFIX}${query}`
}

const query = ref('')
const searchResponse = ref<SearchResponse | null>(null)
const newSearch = ref(true)
const feedbackGiven = ref(false)

function loadSearchState(searchQuery: string) {
  const saved = localStorage.getItem(getStorageKey(searchQuery))
  if (saved) {
    const state = JSON.parse(saved)
    // Check if stored result is less than 30 minutes old
    if (Date.now() - state.timestamp < 30 * 60 * 1000) {
      searchResponse.value = state.results
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

const router = useRouter()
const route = useRoute()

const search = useCall<SearchResponse, SearchParams>({
  url: '/api/v2/method/gameplan.api.search2',
  immediate: false,
  onSuccess(response) {
    searchResponse.value = response
    if (query.value) {
      saveSearchState(query.value, response)
    }
  },
})

onMounted(() => {
  const searchQuery = route.query.q as string
  if (searchQuery) {
    query.value = searchQuery
    if (!loadSearchState(searchQuery)) {
      submit(searchQuery)
    }
  } else {
    clearStoredSearches()
  }
})

function clearSearch() {
  query.value = ''
  searchResponse.value = null
  newSearch.value = true
  feedbackGiven.value = false
  clearStoredSearches()
  router.replace({ query: {} })
}

// Update URL when query changes
function updateQuery(value: string) {
  query.value = value
  router.replace({ query: value ? { q: value } : {} })
}

const submit = debounce(function (text: string) {
  newSearch.value = false
  feedbackGiven.value = false
  query.value = text
  router.replace({ query: text ? { q: text } : {} })
  search.submit({ query: text })
}, 300)

usePageMeta(() => {
  return {
    title: 'Search',
  }
})

function getItemRoute(item: SearchResultItem) {
  switch (item.doctype) {
    case 'GP Discussion':
      return {
        name: 'Discussion',
        params: {
          spaceId: item.project,
          postId: item.name,
        },
      }
    case 'GP Task':
      return {
        name: 'SpaceTask',
        params: {
          spaceId: item.project,
          taskId: item.name,
        },
      }
    case 'GP Page':
      return {
        name: 'SpacePage',
        params: {
          spaceId: item.project,
          pageId: item.name,
        },
      }
    case 'GP Comment':
      if (item.reference_doctype === 'GP Discussion') {
        return {
          name: 'Discussion',
          params: {
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
  background-color: theme('colors.amber.100');
  font-weight: 500;
}
</style>
