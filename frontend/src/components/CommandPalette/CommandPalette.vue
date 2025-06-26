<template>
  <Dialog
    v-model="show"
    :options="{ size: 'xl', position: 'top' }"
    @after-leave="filteredOptions = []"
  >
    <template #body>
      <div class="flex flex-col">
        <div class="relative">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-4.5">
              <LucideSearch class="h-4 w-4 text-ink-gray-6" />
            </div>
            <input
              ref="inputRef"
              type="text"
              placeholder="Search"
              class="w-full border-none bg-transparent py-3 pl-11.5 pr-4.5 text-base text-ink-gray-7 placeholder-ink-gray-4 focus:ring-0"
              @input="onInput"
              @keydown="onKeyDown"
              v-model="query"
              autocomplete="off"
            />
          </div>
          <div
            ref="scrollContainerRef"
            class="max-h-96 overflow-auto border-t border-outline-gray-1 dark:border-outline-gray-2"
            @click="inputRef?.focus()"
          >
            <div
              class="mb-2 mt-4.5 first:mt-3"
              v-for="group in groupedSearchResults"
              :key="group.title"
            >
              <div class="mb-2.5 px-4.5 text-base text-ink-gray-5" v-if="!group.hideTitle">
                {{ group.title }}
              </div>
              <div
                v-for="item in group.items"
                :key="`${item.doctype}:${item.name}`"
                class="px-2.5"
                :class="{ 'pointer-events-none opacity-50': item.disabled }"
              >
                <div
                  @click="onSelection(item)"
                  @mouseover="onItemHover(item)"
                  class="rounded"
                  :class="[item.isActive ? 'bg-surface-gray-3' : '']"
                  :ref="
                    (el) => {
                      if (item.isActive) activeItemRef = el as HTMLDivElement
                    }
                  "
                >
                  <component v-if="group.component" :is="group.component" :item="item" />
                  <Item v-else :item="item" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div
          class="mt-2 flex items-center justify-between border-t border-outline-gray-1 px-2.5 py-2 text-xs text-ink-gray-6 dark:border-outline-gray-2"
        >
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-1">
              <KeyboardShortcut bg>
                <LucideArrowDown class="size-4" />
              </KeyboardShortcut>
              <KeyboardShortcut bg>
                <LucideArrowUp class="size-4" />
              </KeyboardShortcut>
              <span class="ml-1">to navigate</span>
            </div>
            <div class="flex items-center gap-1">
              <KeyboardShortcut bg>
                <LucideCornerDownLeft class="size-4" />
              </KeyboardShortcut>
              <span class="ml-1">to select</span>
            </div>
            <div class="flex items-center gap-1">
              <KeyboardShortcut bg>esc</KeyboardShortcut>
              <span class="ml-1">to close</span>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <KeyboardShortcut bg ctrl>K</KeyboardShortcut>
            <span class="ml-1">to open</span>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import {
  h,
  ref,
  computed,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
  markRaw,
  useTemplateRef,
  type Component,
} from 'vue'
import { RouteLocationRaw, useRouter } from 'vue-router'
import { debounce } from 'frappe-ui'
import { useCall, useNewDoc } from 'frappe-ui/src/data-fetching'
import fuzzysort from 'fuzzysort'
import { activeUsers, useUser } from '@/data/users'
import ItemProject from './ItemProject.vue'
import Item from './Item.vue'
import UserAvatar from '../UserAvatar.vue'
import { spaces, useSpace } from '@/data/spaces'
import { hideCommandPalette, show, toggleCommandPalette } from './commandPalette'
import KeyboardShortcut from '../KeyboardShortcut.vue'

import LucideHome from '~icons/lucide/home'
import LucideUsers from '~icons/lucide/users'
import LucideBell from '~icons/lucide/bell'
import LucideFileSearch from '~icons/lucide/file-search'
import LucideSearch from '~icons/lucide/search'
import LucideCornerDownLeft from '~icons/lucide/corner-down-left'
import LucideArrowDown from '~icons/lucide/arrow-down'
import LucideArrowUp from '~icons/lucide/arrow-up'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideFiles from '~icons/lucide/files'
import LucidePlus from '~icons/lucide/plus'
import LucideMessageSquare from '~icons/lucide/message-square'
import LucideMessageSquarePlus from '~icons/lucide/message-square-plus'
import LucideFilePlus from '~icons/lucide/file-plus'
import LucideSquarePlus from '~icons/lucide/square-plus'
import { showNewTaskDialog } from '../NewTaskDialog'
import { GPPage } from '@/types/doctypes'

const query = ref('')
const filteredOptions = ref<CommandPaletteItem[]>([])
const inputRef = useTemplateRef<HTMLInputElement>('inputRef')
const groupedSearchResults = ref<CommandPaletteGroup[]>([])
const scrollContainerRef = useTemplateRef<HTMLDivElement>('scrollContainerRef')
const activeItemRef = ref<HTMLDivElement | null>(null)

const router = useRouter()

interface SearchResult {
  title: string
  items: SearchResultItem[]
}

interface SearchResultItem {
  author: string
  content: string
  doctype: string
  id: string
  name: string
  project: string
  reference_doctype?: string
  reference_name?: string
  score: number
  timestamp: number
  title: string
}

interface CommandPaletteItem extends Partial<SearchResultItem> {
  title: string
  name: string
  doctype?: string
  route?: RouteLocationRaw
  isActive?: boolean
  group?: string
  type?: string
  modified?: string
  icon?: Component
  onClick?: () => void
  condition?: () => boolean | undefined
  disabled?: boolean
}

interface CommandPaletteGroup {
  title: string
  items: CommandPaletteItem[]
  component?: Component
}

const titleSearch = useCall<SearchResult[], { query: string }>({
  url: '/api/v2/method/gameplan.command_palette.search_sqlite',
  immediate: false,
})

const debouncedTitleSearch = debounce(() => titleSearch.submit({ query: query.value }), 500)

const transformedSearchResults = computed(() => {
  if (!titleSearch.data) return []

  return titleSearch.data.map((group) => ({
    title: group.title,
    items: group.items.map((item) => {
      const baseItem: CommandPaletteItem = { ...item }

      if (group.title === 'Discussions') {
        baseItem.route = {
          name: 'Discussion',
          params: {
            postId: item.name,
            spaceId: item.project,
          },
        }
      } else if (group.title === 'Tasks') {
        baseItem.route = {
          name: item.project ? 'SpaceTask' : 'Task',
          params: {
            taskId: item.name,
            spaceId: item.project,
          },
        }
      } else if (group.title === 'Pages') {
        baseItem.route = {
          name: 'SpacePage',
          params: {
            pageId: item.name,
            spaceId: item.project,
          },
        }
      }

      return baseItem
    }),
  }))
})

const shortcuts = computed((): CommandPaletteGroup[] => [
  {
    title: 'Jump to',
    items: [
      {
        title: 'Advanced Search',
        name: 'search',
        icon: () => h(LucideSearch),
        route: { name: 'Search' },
      },
      {
        title: 'Home',
        name: 'home',
        icon: () => h(LucideHome),
        route: { name: 'Home' },
      },
      {
        title: 'Tasks',
        name: 'tasks',
        icon: () => h(LucideListTodo),
        route: { name: 'MyTasks' },
      },
      {
        title: 'Pages',
        name: 'pages',
        icon: () => h(LucideFiles),
        route: { name: 'MyPages' },
      },
      {
        title: 'People',
        name: 'people',
        icon: () => h(LucideUsers),
        route: { name: 'People' },
        condition: () => useUser().isNotGuest,
      },
      {
        title: 'Inbox',
        name: 'inbox',
        icon: () => h(LucideBell),
        route: { name: 'Notifications' },
        condition: () => useUser().isNotGuest,
      },
    ].filter((item) => (item.condition ? item.condition() : true)),
  },
  {
    title: (() => {
      let spaceId = (router.currentRoute.value.params?.spaceId as string) ?? null
      let space = useSpace(spaceId)
      return space.value ? `Add new in ${space.value.title}` : 'Add new'
    })(),
    items: [
      {
        title: 'Add Discussion',
        name: 'add-discussion',
        icon: () => h(LucideMessageSquarePlus),
        onClick() {
          let spaceId = router.currentRoute.value.params?.spaceId ?? null
          router.push({ name: 'NewDiscussion', query: { spaceId } })
        },
      },
      {
        title: 'Add Task',
        name: 'add-task',
        icon: () => h(LucideSquarePlus),
        onClick() {
          let spaceId = router.currentRoute.value?.params?.spaceId ?? null
          showNewTaskDialog({
            defaults: {
              assigned_to: useUser('sessionUser').name,
              project: spaceId || '',
            },
            onSuccess(doc) {
              if (doc.project) {
                router.push({
                  name: 'SpaceTask',
                  params: { taskId: doc.name, spaceId: doc.project },
                })
              } else {
                router.push({ name: 'Task', params: { taskId: doc.name } })
              }
            },
          })
        },
      },
      {
        title: 'Add Page',
        name: 'add-page',
        icon: () => h(LucideFilePlus),
        onClick() {
          let spaceId = router.currentRoute.value.params?.spaceId ?? null

          const newPage = useNewDoc<GPPage>('GP Page', {
            title: 'Untitled',
            content: '',
          })

          if (spaceId) {
            newPage.doc.project = spaceId as string
          }

          newPage.submit().then((doc) => {
            router.push({
              name: doc.project ? 'SpacePage' : 'Page',
              params: doc.project
                ? { pageId: doc.name, slug: doc.slug, spaceId: doc.project }
                : { pageId: doc.name, slug: doc.slug },
            })
          })
        },
      },
    ],
  },
])

function generateSearchResults() {
  let groups = [{ title: 'Spaces', component: markRaw(ItemProject) }, { title: 'People' }]
  let itemsByGroup: Record<string, CommandPaletteItem[]> = {}
  for (const group of groups) {
    itemsByGroup[group.title] = []
  }

  for (const item of filteredOptions.value) {
    itemsByGroup[item.group || '']?.push(item)
  }
  let localResults = groups
    .map((group) => ({
      ...group,
      items: itemsByGroup[group.title],
    }))
    .filter((group) => group.items.length > 0)

  let titleSearchResults = query.value.length > 2 ? transformedSearchResults.value : []

  // Filter shortcuts based on query
  let filteredShortcuts = shortcuts.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item: CommandPaletteItem) =>
        item.title.toLowerCase().includes(query.value.toLowerCase()),
      ),
    }))
    .filter((group) => group.items.length > 0)

  let results = [...localResults, ...titleSearchResults]

  let fullTextSearchItem: CommandPaletteItem = {
    title: `Search for "${query.value}"`,
    name: 'search-full-text',
    doctype: 'Search',
    icon: () => h(LucideFileSearch),
    route: { name: 'Search', query: { q: query.value } },
  }

  if (query.value.length > 2) {
    if (filteredShortcuts.length === 0) {
      filteredShortcuts.push({
        title: 'Jump to',
        items: [],
      })
    }
    filteredShortcuts[0].items.push(fullTextSearchItem)
  }

  const allResults = [...filteredShortcuts, ...results]

  for (let group of allResults) {
    for (let item of group.items) {
      item.isActive = false
    }
  }

  if (allResults.length > 0 && allResults[0].items.length > 0) {
    allResults[0].items[0].isActive = true
  }

  groupedSearchResults.value = allResults
}

// Watch dependencies and update results
watch([query, filteredOptions, transformedSearchResults], generateSearchResults, {
  immediate: true,
})

const searchList = computed(() => {
  let list: CommandPaletteItem[] = []
  for (const project of spaces.data || []) {
    list.push({
      type: 'Project',
      group: 'Spaces',
      doctype: 'GP Project',
      name: project.name,
      title: project.title,
      modified: project.modified,
      route: {
        name: 'Space',
        params: { spaceId: project.name },
      },
    })
  }

  for (const user of activeUsers.value) {
    list.push({
      type: 'People',
      group: 'People',
      doctype: 'GP User Profile',
      name: user.name,
      title: user.full_name,
      //   modified: user.modified,
      icon: () => h(UserAvatar, { user: user.email, size: 'sm' }),
      route: {
        name: 'PersonProfile',
        params: { personId: user.user_profile },
      },
    })
  }
  return list
})

function onInput(e: Event) {
  query.value = (e.target as HTMLInputElement).value
  if (query.value) {
    let results = fuzzysort
      .go(query.value, searchList.value, {
        key: 'title',
        limit: 100,
        threshold: -10000,
      })
      .map((result) => result.obj)

    filteredOptions.value = results

    if (query.value.length > 2) {
      debouncedTitleSearch()
    }
  } else {
    filteredOptions.value = []
  }
}

function onSelection(value: CommandPaletteItem) {
  if (value) {
    if (value.route) {
      router.push(value.route)
    } else if (value.onClick) {
      value.onClick()
    }
    hideCommandPalette()
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    navigateList(e.key === 'ArrowDown' ? 1 : -1)
  } else if (e.key === 'Enter') {
    const activeItem = groupedSearchResults.value
      .flatMap((group) => group.items)
      .find((item) => item.isActive)
    if (activeItem) {
      onSelection(activeItem)
    }
  } else if (e.key === 'Escape') {
    hideCommandPalette()
  } else {
    if (groupedSearchResults.value.length > 0) {
      if (groupedSearchResults.value[0].items?.length > 0) {
        groupedSearchResults.value[0].items[0].isActive = true
      }
    }
  }
}

function navigateList(direction: number) {
  if (!groupedSearchResults.value.length) return

  const allItems = groupedSearchResults.value.flatMap((group) => group.items)
  const currentIndex = allItems.findIndex((item) => item.isActive)

  if (currentIndex !== -1) {
    allItems[currentIndex].isActive = false
  }

  let newIndex = currentIndex + direction
  if (newIndex < 0) newIndex = allItems.length - 1
  if (newIndex >= allItems.length) newIndex = 0

  allItems[newIndex].isActive = true
  nextTick(scrollActiveItemIntoView)
}

function scrollActiveItemIntoView() {
  if (activeItemRef.value) {
    activeItemRef.value.scrollIntoView({
      block: 'nearest',
    })
  }
}

function onItemHover(hoveredItem: CommandPaletteItem) {
  for (let group of groupedSearchResults.value) {
    for (let item of group.items) {
      item.isActive = false
    }
  }
  hoveredItem.isActive = true
}

watch(show, (value) => {
  if (value) {
    query.value = ''
    filteredOptions.value = []
    generateSearchResults()
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

function addKeyboardShortcut() {
  window.addEventListener('keydown', (e) => {
    if (
      e.key === 'k' &&
      (e.ctrlKey || e.metaKey) &&
      !(e.target as HTMLElement).classList.contains('ProseMirror')
    ) {
      toggleCommandPalette()
      e.preventDefault()
    }
  })
}

onMounted(() => {
  addKeyboardShortcut()
})

onBeforeUnmount(() => {
  hideCommandPalette()
})
</script>
<style>
mark {
  background-color: theme('colors.amber.100');
  font-weight: 500;
}
</style>
