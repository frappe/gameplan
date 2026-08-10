<template>
  <Dialog v-model:open="show" size="xl" position="top" bare @after-leave="filteredOptions = []">
    <div class="command-palette-dialog flex flex-col">
      <Dialog.Title as-child>
        <h2 class="sr-only">Command palette</h2>
      </Dialog.Title>
      <div class="relative">
        <div class="relative">
          <div class="absolute inset-y-0 left-0 flex items-center pl-4.5">
            <span class="lucide-search h-4 w-4 text-ink-gray-6" />
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
            role="combobox"
            aria-autocomplete="list"
            :aria-expanded="show"
            :aria-controls="commandPaletteListId"
            :aria-activedescendant="activeItemId"
          />
        </div>
        <div
          :id="commandPaletteListId"
          ref="scrollContainerRef"
          class="max-h-96 overflow-auto border-t border-outline-gray-1 dark:border-outline-gray-2"
          role="listbox"
          aria-label="Command palette results"
          @click="inputRef?.focus()"
        >
          <div
            class="mb-2 mt-4.5 first:mt-3"
            v-for="group in groupedSearchResults"
            :key="getCommandPaletteGroupKey(group)"
            role="group"
            :aria-labelledby="getCommandPaletteGroupId(group)"
          >
            <div
              :id="getCommandPaletteGroupId(group)"
              class="mb-2.5 px-4.5 text-base text-ink-gray-5"
              v-if="!group.hideTitle"
            >
              {{ group.title }}
            </div>
            <div
              v-for="item in group.items"
              :key="getCommandPaletteItemKey(item)"
              class="px-2.5"
              :class="{ 'pointer-events-none opacity-50': item.disabled }"
            >
              <div
                :id="getCommandPaletteItemElementId(item)"
                @click="onSelection(item)"
                @mousemove="onItemMouseMove(item, $event)"
                class="rounded-4"
                :class="[item.isActive ? 'bg-surface-gray-3' : '']"
                role="option"
                :aria-selected="item.isActive ? 'true' : 'false'"
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
              <span class="lucide-arrow-down size-4" />
            </KeyboardShortcut>
            <KeyboardShortcut bg>
              <span class="lucide-arrow-up size-4" />
            </KeyboardShortcut>
            <span class="ml-1">to navigate</span>
          </div>
          <div class="flex items-center gap-1">
            <KeyboardShortcut bg>
              <span class="lucide-corner-down-left size-4" />
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
  </Dialog>
</template>

<script setup lang="ts">
import { h, ref, computed, onBeforeUnmount, watch, nextTick, markRaw, useTemplateRef } from 'vue'
import { useEventListener, useMediaQuery } from '@vueuse/core'
import { useRouter } from 'vue-router'
import { Dialog, dayjs, debounce, useCall, useNewDoc } from 'frappe-ui'
import { activeUsers, isGameplanAdmin, useSessionUser, useUser } from '@/data/users'
import ItemProject from './ItemProject.vue'
import Item from './Item.vue'
import UserAvatar from '../UserAvatar.vue'
import CommunityImage from '../CommunityImage.vue'
import { getSpace, spaces, useSpace } from '@/data/spaces'
import { communityState } from '@/data/communityState'
import { activeCommunities } from '@/data/communities'
import { readOnlyMode } from '@/data/readOnlyMode'
import { hideCommandPalette, show, toggleCommandPalette } from './commandPalette'
import KeyboardShortcut from '../KeyboardShortcut.vue'

import { showNewTaskDialog } from '../NewTaskDialog'
import { GPPage } from '@/types/doctypes'
import { showCommunitiesSettings, showSettingsDialog } from '@/components/Settings'
import { useCanManageCommunities } from '@/composables/useCanManageCommunities'
import {
  registeredCommands,
  type CommandPaletteGroup,
  type CommandPaletteItem,
  type SearchResult,
  type SearchResultItem,
} from './registry'
import { useCommandPaletteSearch } from './useCommandPaletteSearch'

const query = ref('')
const inputRef = useTemplateRef<HTMLInputElement>('inputRef')
const scrollContainerRef = useTemplateRef<HTMLDivElement>('scrollContainerRef')
const activeItemRef = ref<HTMLDivElement | null>(null)
const commandPaletteListId = 'command-palette-listbox'

const router = useRouter()
const sessionUser = useSessionUser()
const canManageCommunities = useCanManageCommunities()
const activeCommunityIds = computed(
  () => new Set(activeCommunities.value.map((community) => community.name)),
)
const activeCommunityById = computed(
  () => new Map(activeCommunities.value.map((community) => [community.name, community])),
)
const currentSpace = computed(() => {
  const spaceId = router.currentRoute.value.params?.spaceId
  return typeof spaceId === 'string' ? getSpace(spaceId) : null
})
const canCreateFromPalette = computed(() => !readOnlyMode && !currentSpace.value?.archived_at)
// The profile customize page needs an editor panel beside the canvas, so it only
// renders from `md` up. Read inside a condition so `shortcuts` re-evaluates on resize.
const canCustomizeProfile = useMediaQuery('(min-width: 768px)')
const normalizedQuery = computed(() => query.value.trim())
const serverSearchQuery = ref('')
const serverSearchResults = ref<SearchResult[]>([])

const titleSearch = useCall<SearchResult[], { query: string }>({
  url: '/api/v2/method/gameplan.command_palette.search_sqlite',
  immediate: false,
})

const debouncedTitleSearch = debounce(submitTitleSearch, 500)

const transformedSearchResults = computed(() => {
  if (!serverSearchResults.value.length) return []
  if (serverSearchQuery.value !== normalizedQuery.value) return []

  return serverSearchResults.value
    .map((group) => ({
      title: group.title,
      items: group.items.filter(isSearchItemVisible).map((item) => {
        const baseItem: CommandPaletteItem = {
          ...item,
          modified: dayjs.unix(item.modified).format('YYYY-MM-DD HH:mm:ss'),
        }

        if (group.title === 'Discussions') {
          baseItem.route = {
            name: 'Discussion',
            params: {
              communityId: item.team || getSpace(item.project)?.team,
              postId: item.name,
              spaceId: item.project,
            },
          }
        } else if (group.title === 'Tasks') {
          baseItem.route = {
            name: item.project ? 'SpaceTask' : 'Task',
            params: item.project
              ? {
                  communityId: item.team || getSpace(item.project)?.team,
                  taskId: item.name,
                  spaceId: item.project,
                }
              : {
                  taskId: item.name,
                },
          }
        } else if (group.title === 'Pages') {
          baseItem.route = {
            name: 'SpacePage',
            params: {
              communityId: item.team || getSpace(item.project)?.team,
              pageId: item.name,
              spaceId: item.project,
            },
          }
        }

        return baseItem
      }),
    }))
    .filter((group) => group.items.length > 0)
})

const shortcuts = computed((): CommandPaletteGroup[] => [
  {
    title: 'Jump to',
    items: [
      {
        title: 'Advanced Search',
        name: 'search',
        icon: 'lucide-search',
        aliases: ['full text search', 'find'],
        route: { name: 'Search' },
      },
      {
        title: 'Home',
        name: 'home',
        icon: 'lucide-home',
        aliases: ['dashboard', 'start'],
        route: { name: 'Home' },
      },
      {
        title: 'Drafts',
        name: 'drafts',
        icon: 'lucide-pencil-line',
        aliases: ['saved drafts'],
        route: { name: 'Drafts' },
      },
      {
        title: 'Bookmarks',
        name: 'bookmarks',
        icon: 'lucide-bookmark',
        aliases: ['saved', 'saved posts'],
        route: { name: 'Bookmarks' },
      },
      {
        title: 'Tasks',
        name: 'tasks',
        icon: 'lucide-list-todo',
        aliases: ['my tasks', 'todos', 'todo'],
        route: { name: 'MyTasks' },
      },
      {
        title: 'Pages',
        name: 'pages',
        icon: 'lucide-files',
        aliases: ['my pages', 'docs', 'documents', 'wiki'],
        route: { name: 'MyPages' },
      },
      {
        title: 'People',
        name: 'people',
        icon: 'lucide-users',
        aliases: ['users', 'members', 'team'],
        route: { name: 'People' },
        condition: () => useUser().isNotGuest,
      },
      {
        title: 'Notifications',
        name: 'notifications',
        icon: 'lucide-bell',
        aliases: ['inbox', 'mentions', 'activity'],
        route: { name: 'Notifications' },
        condition: () => useUser().isNotGuest,
      },
      {
        title: 'Customize Profile',
        name: 'customize-profile',
        icon: 'lucide-user-pen',
        aliases: ['profile bento', 'edit profile'],
        route: { name: 'ProfileCustomize' },
        condition: () => useUser().isNotGuest && canCustomizeProfile.value,
      },
    ].filter((item) => (item.condition ? item.condition() : true)),
  },
  {
    title: 'Settings',
    items: [
      {
        title: 'Profile',
        name: 'settings-profile',
        icon: 'lucide-user',
        search: 'Settings Profile account',
        aliases: ['account', 'profile'],
        onClick: () => showSettingsDialog('Profile'),
      },
      {
        title: 'Preferences',
        name: 'settings-preferences',
        icon: 'lucide-sliders-horizontal',
        search: 'Settings Preferences sidebar reactions appearance',
        aliases: ['sidebar', 'reactions', 'appearance'],
        onClick: () => showSettingsDialog('Preferences'),
      },
      {
        title: 'Notifications',
        name: 'settings-notifications',
        icon: 'lucide-bell',
        search: 'Settings Notifications email digest alerts',
        aliases: ['email digest', 'digest', 'alerts'],
        onClick: () => showSettingsDialog('Notifications'),
      },
      {
        title: 'Custom Emojis',
        name: 'settings-custom-emojis',
        icon: 'lucide-smile-plus',
        search: 'Settings Custom Emojis emoji settings upload emoji',
        aliases: ['emoji settings', 'upload emoji'],
        onClick: () => showSettingsDialog('Emojis'),
        condition: () => isGameplanAdmin(sessionUser),
      },
      {
        title: 'Communities',
        name: 'settings-communities',
        icon: 'lucide-building-2',
        search: 'Settings Communities manage communities manage spaces spaces settings',
        aliases: ['communities settings', 'manage spaces', 'spaces settings'],
        onClick: () => showCommunitiesSettings(),
        condition: () => canManageCommunities.value,
      },
      {
        title: 'Users',
        name: 'settings-users',
        icon: 'lucide-users',
        search: 'Settings Users members invite users administration',
        aliases: ['members', 'invite users', 'administration'],
        onClick: () => showSettingsDialog('Users'),
        condition: () => isGameplanAdmin(sessionUser),
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
        search: 'Add Discussion New Discussion',
        aliases: ['new discussion', 'start discussion', 'post'],
        icon: 'lucide-message-square-plus',
        condition: () => canCreateFromPalette.value,
        onClick() {
          let spaceId = router.currentRoute.value.params?.spaceId ?? null
          let communityId = router.currentRoute.value.params?.communityId ?? communityState.id

          if (!communityId) {
            router.push({ name: 'LegacyNewDiscussion', query: { spaceId } })
            return
          }

          router.push({ name: 'NewDiscussion', params: { communityId }, query: { spaceId } })
        },
      },
      {
        title: 'Add Task',
        name: 'add-task',
        search: 'Add Task New Task',
        aliases: ['new task', 'todo', 'create task'],
        icon: 'lucide-square-plus',
        condition: () => canCreateFromPalette.value,
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
                  params: {
                    communityId: getSpace(doc.project)?.team,
                    taskId: doc.name,
                    spaceId: doc.project,
                  },
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
        search: 'Add Page New Page',
        aliases: ['new page', 'doc', 'document', 'note'],
        icon: 'lucide-file-plus',
        condition: () => canCreateFromPalette.value,
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
                ? {
                    communityId: getSpace(doc.project)?.team,
                    pageId: doc.name,
                    slug: doc.slug,
                    spaceId: doc.project,
                  }
                : { pageId: doc.name, slug: doc.slug },
            })
          })
        },
      },
    ].filter((item) => (item.condition ? item.condition() : true)),
  },
])

function getCommandSourceGroups() {
  return [...groupRegisteredCommands(), ...shortcuts.value]
}

function groupRegisteredCommands() {
  let groups: CommandPaletteGroup[] = []

  for (const command of registeredCommands.value) {
    if (command.condition && !command.condition()) continue

    let title = command.group || 'Actions'
    let group = groups.find((group) => group.title === title)
    if (!group) {
      group = { title, items: [] }
      groups.push(group)
    }
    group.items.push(command)
  }

  return groups
}

/**
 * Every person appears once per destination, titled "<name> / <tab>" so the name a query
 * matches on stays at the front. The three rows share a cluster key, which holds them
 * together in the results instead of letting another person's rows slot between them.
 */
const personTabs = [
  { route: 'PersonProfileProfile', label: 'Profile', keywords: 'profile about bio' },
  { route: 'PersonProfilePosts', label: 'Posts', keywords: 'posts discussions written' },
  { route: 'PersonProfileReplies', label: 'Replies', keywords: 'replies comments' },
] as const

const searchList = computed(() => {
  let list: CommandPaletteItem[] = []
  for (const community of activeCommunities.value) {
    list.push({
      type: 'Community',
      group: 'communities',
      doctype: 'GP Team',
      name: community.name,
      title: community.title,
      search: `${community.title} ${community.name} community switch`,
      icon: () => h(CommunityImage, { community, class: 'size-4' }),
      onClick: () => switchCommunity(community.name),
    })
  }

  for (const project of spaces.data || []) {
    if (project.archived_at || !activeCommunityIds.value.has(project.team)) continue

    list.push({
      type: 'Project',
      group: getCommunityGroupId(project.team),
      doctype: 'GP Project',
      name: project.name,
      title: project.title,
      search: `${project.title} ${project.team} ${getCommunityTitle(project.team)}`,
      hideCommunity: true,
      route: {
        name: 'Space',
        params: { communityId: project.team, spaceId: project.name },
      },
    })
  }

  for (const user of activeUsers.value) {
    for (const tab of personTabs) {
      list.push({
        type: 'People',
        group: 'people',
        cluster: user.name,
        doctype: 'GP User Profile',
        name: `${user.name}:${tab.route}`,
        title: `${user.full_name} / ${tab.label}`,
        search: `${user.full_name} ${user.email} ${tab.keywords}`,
        icon: () => h(UserAvatar, { user: user.email, size: 'sm' }),
        route: {
          name: tab.route,
          params: { personId: user.user_profile },
        },
      })
    }
  }
  return list
})

const localResultGroups = computed(() => [
  { id: 'communities', title: 'Communities' },
  ...activeCommunities.value.map((community) => ({
    id: getCommunityGroupId(community.name),
    title: community.title,
    component: markRaw(ItemProject),
  })),
  { id: 'people', title: 'People' },
])

const commandSourceGroups = computed(() => getCommandSourceGroups())

const {
  activeItem,
  activeItemId,
  activateItem,
  filteredOptions,
  generateSearchResults,
  getCommandPaletteGroupId,
  getCommandPaletteGroupKey,
  getCommandPaletteItemElementId,
  getCommandPaletteItemKey,
  groupedSearchResults,
  navigateList,
  updateLocalResults,
} = useCommandPaletteSearch({
  query,
  commandGroups: commandSourceGroups,
  localItems: searchList,
  localGroups: localResultGroups,
  serverGroups: transformedSearchResults,
})

function switchCommunity(communityId: string) {
  communityState.change(communityId)
  router.push({ name: 'Discussions', params: { communityId } })
}

function getCommunityGroupId(communityId: string) {
  return `community:${communityId}`
}

function getCommunityTitle(communityId: string) {
  return activeCommunityById.value.get(communityId)?.title || communityId
}

function isSearchItemVisible(item: SearchResultItem) {
  if (!item.project) return true

  const space = getSpace(item.project)
  return Boolean(space && !space.archived_at && activeCommunityIds.value.has(space.team))
}

function onInput(e: Event) {
  query.value = (e.target as HTMLInputElement).value
  updateLocalResults()

  if (normalizedQuery.value.length > 2) {
    debouncedTitleSearch()
  } else {
    clearTitleSearchResults()
  }
}

async function submitTitleSearch() {
  const submittedQuery = normalizedQuery.value
  if (submittedQuery.length <= 2) {
    clearTitleSearchResults()
    return
  }

  const response = await (titleSearch.submit({ query: submittedQuery }) as Promise<
    SearchResult[] | null
  >)
  if (submittedQuery !== normalizedQuery.value) return

  serverSearchQuery.value = submittedQuery
  serverSearchResults.value = response || []
}

function clearTitleSearchResults() {
  serverSearchQuery.value = ''
  serverSearchResults.value = []
}

function onSelection(value: CommandPaletteItem) {
  if (value.disabled) return

  hideCommandPalette()

  if (value.route) {
    router.push(value.route)
  } else if (value.onClick) {
    requestAnimationFrame(() => {
      value.onClick?.()
    })
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    navigateList(e.key === 'ArrowDown' ? 1 : -1)
    nextTick(scrollActiveItemIntoView)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    e.stopPropagation()
    if (activeItem.value) {
      onSelection(activeItem.value)
    }
  } else if (e.key === 'Escape') {
    hideCommandPalette()
  }
}

function scrollActiveItemIntoView() {
  if (activeItemRef.value) {
    activeItemRef.value.scrollIntoView({
      block: 'nearest',
    })
  }
}

function onItemMouseMove(hoveredItem: CommandPaletteItem, event: MouseEvent) {
  if (event.movementX === 0 && event.movementY === 0) return

  activateItem(hoveredItem)
}

watch(show, (value) => {
  if (value) {
    query.value = ''
    filteredOptions.value = []
    clearTitleSearchResults()
    generateSearchResults({ preserveActive: false })
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})

// useEventListener auto-removes on unmount, so remounting across the 640px
// layout breakpoint can't stack duplicate keydown handlers (the V2 leak).
useEventListener(window, 'keydown', (e: KeyboardEvent) => {
  const target = e.target as HTMLElement | null
  if (e.key === 'k' && (e.ctrlKey || e.metaKey) && !target?.classList?.contains('ProseMirror')) {
    toggleCommandPalette()
    e.preventDefault()
  }
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

.dialog-overlay:has(.command-palette-dialog),
.dialog-content:has(.command-palette-dialog) {
  animation: none !important;
}
</style>
