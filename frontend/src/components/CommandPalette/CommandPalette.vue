<template>
  <Dialog
    v-model="show"
    :options="{ size: 'xl', position: 'top' }"
    @after-leave="filteredOptions = []"
  >
    <template #body>
      <div>
        <Combobox nullable @update:model-value="onSelection" v-slot="{ activeIndex }">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-4.5">
              <LucideSearch class="h-4 w-4 text-ink-gray-7" />
            </div>
            <ComboboxInput
              placeholder="Search"
              class="w-full border-none bg-transparent py-3 pl-11.5 pr-4.5 text-base text-ink-gray-8 placeholder-ink-gray-4 focus:ring-0"
              @input="onInput"
              autocomplete="off"
            />
          </div>
          <ComboboxOptions
            class="max-h-96 overflow-auto border-t border-outline-gray-1 dark:border-outline-gray-2"
            static
            :hold="true"
          >
            <div
              class="mb-2 mt-4.5 first:mt-3"
              v-for="(group, index) in groupedSearchResults"
              :key="group.title"
            >
              <div class="mb-2.5 px-4.5 text-base text-ink-gray-5" v-if="!group.hideTitle">
                {{ group.title }}
              </div>
              <ComboboxOption
                v-for="item in group.items"
                :key="`${item.doctype}:${item.name}`"
                v-slot="{ active }"
                :value="item"
                class="px-2.5"
                :disabled="item.disabled"
              >
                <component :is="group.component" :item="item" :active="active" />
              </ComboboxOption>
            </div>
          </ComboboxOptions>
        </Combobox>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { h, ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Combobox, ComboboxInput, ComboboxOptions, ComboboxOption } from '@headlessui/vue'
import { debounce } from 'frappe-ui'
import { useCall } from 'frappe-ui/src/data-fetching'
import fuzzysort from 'fuzzysort'
import { activeUsers, useUser } from '@/data/users'
import ItemProject from './ItemProject.vue'
import Item from './Item.vue'
import UserAvatar from '../UserAvatar.vue'
import { spaces } from '@/data/spaces'
import { hideCommandPalette, show, toggleCommandPalette } from './commandPalette'
import LucideHome from '~icons/lucide/home'
import LucideUsers from '~icons/lucide/users'
import LucideBell from '~icons/lucide/bell'
import LucideSearch from '~icons/lucide/file-search'

const query = ref('')
const filteredOptions = ref([])
const router = useRouter()

const search = useCall({
  url: '/api/v2/gameplan.command_palette.search',
  immediate: false,
  transform(groups) {
    for (let group of groups) {
      if (group.title === 'Discussions') {
        group.component = Item
        group.items = group.items.map((item) => {
          item.route = {
            name: 'Discussion',
            params: {
              postId: item.name,
              spaceId: item.payload.project,
            },
          }
          return item
        })
      }
      if (group.title === 'Tasks') {
        group.component = Item
        group.items = group.items.map((item) => {
          item.route = {
            name: item.project ? 'SpaceTask' : 'Task',
            params: {
              taskId: item.name,
              spaceId: item.payload.project,
            },
          }
          return item
        })
      }
      if (group.title === 'Pages') {
        group.component = Item
        group.items = group.items.map((item) => {
          item.route = {
            name: 'SpacePage',
            params: {
              pageId: item.name,
              spaceId: item.payload.project,
            },
          }
          return item
        })
      }
    }
    return groups
  },
})

const submitSearch = debounce((query) => search.submit({ query }), 300)

watch(show, (value) => {
  if (value) {
    query.value = ''
  }
})

const searchList = computed(() => {
  let list = []
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
      modified: user.modified,
      icon: () => h(UserAvatar, { user: user.email, size: 'sm' }),
      route: {
        name: 'PersonProfile',
        params: { personId: user.user_profile },
      },
    })
  }
  return list
})

const navigationItems = computed(() => ({
  title: 'Jump to',
  component: Item,
  items: [
    {
      title: 'Home',
      icon: () => h(LucideHome),
      route: { name: 'Home' },
    },
    {
      title: 'People',
      icon: () => h(LucideUsers),
      route: { name: 'People' },
      condition: () => useUser().isNotGuest,
    },
    {
      title: 'Inbox',
      icon: () => h(LucideBell),
      route: { name: 'Notifications' },
      condition: () => useUser().isNotGuest,
    },
  ].filter((item) => (item.condition ? item.condition() : true)),
}))

const fullSearchItem = computed(() => ({
  title: 'Search',
  hideTitle: true,
  component: Item,
  items: [
    {
      title: `Search for "${query.value}"`,
      icon: () => h(LucideSearch),
      route: { name: 'Search', query: { q: query.value } },
    },
  ],
}))

const groupedSearchResults = computed(() => {
  let groups = [
    { title: 'Spaces', component: ItemProject },
    { title: 'People', component: Item },
  ]
  let itemsByGroup = {}
  for (const group of groups) {
    itemsByGroup[group.title] = []
  }
  for (const item of filteredOptions.value) {
    itemsByGroup[item.group].push(item)
  }
  let localResults = groups
    .map((group) => ({
      ...group,
      items: itemsByGroup[group.title],
    }))
    .filter((group) => group.items.length > 0)

  let serverResults = query.value.length > 2 && search.data ? search.data : []
  let results = [...localResults, ...serverResults]
  return [
    ...(query.value.length > 2 ? [fullSearchItem.value] : []),
    ...(results.length === 0 ? [navigationItems.value] : []),
    ...results,
  ]
})

function onInput(e) {
  query.value = e.target.value
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
      submitSearch(query.value)
    }
  } else {
    filteredOptions.value = []
  }
}

function onSelection(value) {
  if (value) {
    router.push(value.route)
    hideCommandPalette()
  }
}

function addKeyboardShortcut() {
  window.addEventListener('keydown', (e) => {
    if (e.key === 'k' && (e.ctrlKey || e.metaKey) && !e.target.classList.contains('ProseMirror')) {
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
