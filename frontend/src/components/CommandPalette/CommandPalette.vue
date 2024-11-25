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
<script>
import { h, ref } from 'vue'
import { Combobox, ComboboxInput, ComboboxOptions, ComboboxOption } from '@headlessui/vue'
import fuzzysort from 'fuzzysort'
import { activeTeams } from '@/data/teams'
import { activeProjects } from '@/data/projects'
import { activeUsers } from '@/data/users'
import ItemTeam from './ItemTeam.vue'
import ItemProject from './ItemProject.vue'
import Item from './Item.vue'
import UserAvatar from '../UserAvatar.vue'
import LucideHome from '~icons/lucide/home'
import LucideUsers from '~icons/lucide/users'
import LucideBell from '~icons/lucide/bell'
import LucideSearch from '~icons/lucide/file-search'

let show = ref(false)

export function showCommandPalette() {
  show.value = true
}

export function hideCommandPalette() {
  show.value = false
}

export function toggleCommandPalette() {
  show.value = !show.value
}

export default {
  name: 'CommandPalette',
  data() {
    return {
      query: '',
      filteredOptions: [],
    }
  },
  resources: {
    search() {
      return {
        url: 'gameplan.command_palette.search',
        makeParams(query) {
          return { query }
        },
        debounce: 300,
        transform(groups) {
          for (let group of groups) {
            if (group.title === 'Discussions') {
              group.component = 'Item'
              group.items = group.items.map((item) => {
                item.route = {
                  name: 'ProjectDiscussion',
                  params: {
                    postId: item.name,
                    projectId: item.payload.project,
                    teamId: item.payload.team,
                  },
                }
                return item
              })
            }
            if (group.title === 'Tasks') {
              group.component = 'Item'
              group.items = group.items.map((item) => {
                item.route = {
                  name: item.project ? 'ProjectTaskDetail' : 'Task',
                  params: {
                    taskId: item.name,
                    projectId: item.payload.project,
                    teamId: item.payload.team,
                  },
                }
                return item
              })
            }
            if (group.title === 'Pages') {
              group.component = 'Item'
              group.items = group.items.map((item) => {
                item.route = {
                  name: 'ProjectPage',
                  params: {
                    pageId: item.name,
                    projectId: item.payload.project,
                    teamId: item.payload.team,
                  },
                }
                return item
              })
            }
          }
          return groups
        },
      }
    },
  },
  watch: {
    show(value) {
      if (value) {
        this.query = ''
      }
    },
  },
  setup() {
    return { show }
  },
  components: {
    Combobox,
    ComboboxInput,
    ComboboxOptions,
    ComboboxOption,
    ItemTeam,
    ItemProject,
    Item,
  },
  mounted() {
    this.addKeyboardShortcut()
  },
  beforeUnmount() {
    hideCommandPalette()
  },
  methods: {
    onInput(e) {
      this.query = e.target.value
      if (this.query) {
        let results = fuzzysort
          .go(this.query, this.searchList, {
            key: 'title',
            limit: 100,
            threshold: -10000,
          })
          .map((result) => result.obj)

        this.filteredOptions = results

        if (this.query.length > 2) {
          this.$resources.search.submit(this.query)
        }
      } else {
        this.filteredOptions = []
      }
    },
    onSelection(value) {
      if (value) {
        this.$router.push(value.route)
        hideCommandPalette()
      }
    },
    addKeyboardShortcut() {
      window.addEventListener('keydown', (e) => {
        if (
          e.key === 'k' &&
          (e.ctrlKey || e.metaKey) &&
          !e.target.classList.contains('ProseMirror')
        ) {
          toggleCommandPalette()
          e.preventDefault()
        }
      })
    },
  },
  computed: {
    searchList() {
      let list = []
      let teamsByName = {}
      for (const team of activeTeams.value) {
        teamsByName[team.name] = team
        list.push({
          type: 'Team',
          group: 'Teams',
          doctype: 'GP Team',
          name: team.name,
          title: team.title,
          icon: team.icon,
          modified: team.modified,
          route: {
            name: 'Team',
            params: { teamId: team.name },
          },
        })
      }

      for (const project of activeProjects.value) {
        let team = teamsByName[project.team] || null
        list.push({
          type: 'Project',
          group: 'Projects',
          doctype: 'GP Project',
          name: project.name,
          title: project.title,
          team: team?.title,
          modified: project.modified,
          route: {
            name: 'Project',
            params: { teamId: project.team, projectId: project.name },
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
    },
    navigationItems() {
      return {
        title: 'Jump to',
        component: 'Item',
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
            condition: () => this.$user().isNotGuest,
          },
          {
            title: 'Notifications',
            icon: () => h(LucideBell),
            route: { name: 'Notifications' },
            condition: () => this.$user().isNotGuest,
          },
        ].filter((item) => (item.condition ? item.condition() : true)),
      }
    },
    fullSearchItem() {
      return {
        title: 'Search',
        hideTitle: true,
        component: 'Item',
        items: [
          {
            title: `Search for "${this.query}"`,
            icon: () => h(LucideSearch),
            route: { name: 'Search', query: { q: this.query } },
          },
        ],
      }
    },
    groupedSearchResults() {
      let groups = [
        { title: 'Teams', component: 'ItemTeam' },
        { title: 'Projects', component: 'ItemProject' },
        { title: 'People', component: 'Item' },
      ]
      let itemsByGroup = {}
      for (const group of groups) {
        itemsByGroup[group.title] = []
      }
      for (const item of this.filteredOptions) {
        itemsByGroup[item.group].push(item)
      }
      let localResults = groups
        .map((group) => {
          return {
            ...group,
            items: itemsByGroup[group.title],
          }
        })
        .filter((group) => group.items.length > 0)

      let serverResults =
        this.query.length > 2 && this.$resources.search.data ? this.$resources.search.data : []
      let results = [...localResults, ...serverResults]
      return [
        ...(this.query.length > 2 ? [this.fullSearchItem] : []),
        ...(results.length === 0 ? [this.navigationItems] : []),
        ...results,
      ]
    },
  },
}
</script>
