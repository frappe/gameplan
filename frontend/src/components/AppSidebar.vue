<template>
  <TransitionRoot as="template" :show="sidebarOpen">
    <Dialog
      as="div"
      class="fixed inset-0 z-40 flex md:hidden"
      @close="$emit('update:sidebarOpen', false)"
    >
      <TransitionChild
        as="template"
        enter="transition-opacity ease-linear duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="transition-opacity ease-linear duration-300"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <DialogOverlay class="fixed inset-0 bg-gray-600 bg-opacity-75" />
      </TransitionChild>
      <TransitionChild
        as="template"
        enter="transition ease-in-out duration-300 transform"
        enter-from="-translate-x-full"
        enter-to="translate-x-0"
        leave="transition ease-in-out duration-300 transform"
        leave-from="translate-x-0"
        leave-to="-translate-x-full"
      >
        <div class="relative flex flex-col flex-1 w-full max-w-xs bg-white">
          <TransitionChild
            as="template"
            enter="ease-in-out duration-300"
            enter-from="opacity-0"
            enter-to="opacity-100"
            leave="ease-in-out duration-300"
            leave-from="opacity-100"
            leave-to="opacity-0"
          >
            <div class="absolute top-0 right-0 pt-2 -mr-12">
              <button
                type="button"
                class="flex items-center justify-center w-10 h-10 ml-1 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                @click="$emit('update:sidebarOpen', false)"
              >
                <span class="sr-only">Close sidebar</span>
                <FeatherIcon
                  name="x"
                  class="w-6 h-6 text-white"
                  aria-hidden="true"
                />
              </button>
            </div>
          </TransitionChild>
          <div class="flex-1 h-0 pt-5 pb-4 overflow-y-auto">
            <div class="flex items-center flex-shrink-0 px-4">Teams</div>
            <nav class="px-2 mt-5 space-y-1">
              <router-link
                v-for="item in navigation"
                :key="item.name"
                :to="item.route"
                :class="[
                  false
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                  'group flex items-center px-2 py-2 text-base font-medium rounded-md',
                ]"
              >
                {{ item.name }}
              </router-link>
            </nav>
          </div>
          <div class="flex flex-shrink-0 p-4 border-t border-gray-200">
            <a href="#" class="flex-shrink-0 block group">
              <div class="flex items-center">
                <div>
                  <img
                    class="inline-block w-10 h-10 rounded-full"
                    src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                    alt
                  />
                </div>
                <div class="ml-3">
                  <p
                    class="text-base font-medium text-gray-700 group-hover:text-gray-900"
                  >
                    Tom Cook
                  </p>
                  <p
                    class="text-sm font-medium text-gray-500 group-hover:text-gray-700"
                  >
                    View profile
                  </p>
                </div>
              </div>
            </a>
          </div>
        </div>
      </TransitionChild>
      <div class="flex-shrink-0 w-14"></div>
    </Dialog>
  </TransitionRoot>

  <!-- Static sidebar for desktop -->
  <div class="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
    <!-- Sidebar component, swap this element with another sidebar if you like -->
    <div class="flex flex-col flex-1 min-h-0">
      <div class="flex flex-col flex-1 pt-5 pb-4 overflow-y-auto">
        <div class="grid px-2">
          <UserDropdown />
        </div>
        <div class="flex-1 mt-5">
          <nav class="px-2 space-y-1">
            <Links
              :links="navigation"
              class="flex items-center px-2 py-2 font-medium rounded-md"
              active="bg-white text-gray-900"
              inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <template v-slot="{ link }">
                <span class="inline-flex items-center space-x-2">
                  <span class="grid w-5 h-5 place-items-center">
                    <FeatherIcon :name="link.icon" class="w-4 h-4" />
                  </span>
                  <span class="text-lg">{{ link.name }}</span>
                </span>
              </template>
            </Links>
          </nav>
          <div class="flex items-center justify-between px-3 mt-8">
            <h3
              class="text-xs font-semibold tracking-wider text-gray-500 uppercase"
            >
              Your Teams
            </h3>
            <Button icon="plus" @click="showAddTeamDialog = true">
              Create Team
            </Button>
          </div>
          <nav class="px-2 mt-1 space-y-1">
            <div v-for="team in $resources.teams.data" :key="team.name">
              <Link
                :link="team"
                class="flex items-center px-2 py-2 font-medium rounded-md"
                exact-active="bg-gray-200 text-gray-900"
                inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              >
                <button
                  @click.prevent="
                    () => {
                      team.open = !team.open
                      if (team.projects.data == null) {
                        team.projects.fetch()
                      }
                    }
                  "
                  class="grid w-5 h-5 mr-2 rounded place-items-center hover:bg-gray-200"
                >
                  <FeatherIcon
                    :name="team.open ? 'chevron-down' : 'chevron-right'"
                    class="w-4 h-4"
                  />
                </button>
                <span class="inline-flex items-center space-x-2">
                  <span
                    class="flex items-center justify-center w-5 h-5 text-xl"
                  >
                    {{ team.icon }}
                  </span>
                  <span class="text-lg">{{ team.title }}</span>
                </span>
              </Link>
              <div v-show="team.open">
                <Links
                  :links="team.projects.data || []"
                  class="flex items-center py-1.5 mt-0.5 pl-12 pr-2 font-medium rounded-md"
                  active="bg-gray-200 text-gray-900"
                  inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <template v-slot="{ link }">
                    <span class="inline-flex items-center space-x-2">
                      <span
                        class="flex items-center justify-center w-5 h-5 text-xl"
                      >
                        {{ link.icon }}
                      </span>
                      <span class="text-base">{{ link.title }}</span>
                    </span>
                  </template>
                </Links>
              </div>
            </div>
          </nav>
          <div
            v-if="$resources.teams.fetched && !$resources.teams.data.length"
            class="px-3 py-2 text-sm text-gray-500"
          >
            No teams
          </div>
        </div>
      </div>
    </div>
  </div>
  <AddTeamDialog
    v-model:show="showAddTeamDialog"
    @success="
      (team) => {
        showAddTeamDialog = false
        $resources.teams.fetch()
        $router.push(`/${team.name}`)
      }
    "
  />
</template>

<script>
import {
  Dialog,
  DialogOverlay,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue'
import { createResource } from 'frappe-ui'
import Links from './Links.vue'
import Link from './Link.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import UserDropdown from './UserDropdown.vue'

export default {
  name: 'AppSidebar',
  props: ['sidebarOpen'],
  emits: ['update:sidebarOpen'],
  components: {
    Dialog,
    DialogOverlay,
    TransitionRoot,
    TransitionChild,
    AddTeamDialog,
    Links,
    Link,
    UserDropdown,
  },
  data() {
    return {
      navigation: [
        {
          name: 'Home',
          icon: 'home',
          route: {
            name: 'Home',
          },
        },
        {
          name: 'People',
          icon: 'users',
          route: {
            name: 'People',
          },
        },
        // {
        //   name: 'Daily Planner',
        //   icon: 'edit',
        //   route: {
        //     name: 'DailyPlanner',
        //   },
        // },
        // {
        //   name: 'Tasks',
        //   icon: 'clipboard',
        //   route: {
        //     name: 'Tasks',
        //   },
        // },
        // { name: 'Inbox', icon: 'inbox', route: '/inbox' },
      ],
      showAddTeamDialog: false,
    }
  },
  resources: {
    teams: {
      type: 'list',
      doctype: 'Team',
      fields: ['name', 'title', 'icon', 'modified', 'creation'],
      order_by: 'creation asc',
      cache: 'Sidebar Teams',
      transform(data) {
        return data.map((team) => {
          return {
            ...team,
            route: {
              name: 'TeamPageHome',
              params: { teamId: team.name },
            },
            open: false,
            projects: this.createProjectsResource(team.name),
          }
        })
      },
    },
  },
  methods: {
    createProjectsResource(team) {
      return createResource({
        method: 'frappe.client.get_list',
        params: {
          doctype: 'Team Project',
          filters: { team },
          fields: ['name', 'title', 'icon', 'team'],
          order_by: 'creation asc',
        },
        cache: ['Team Project List', team],
        transform(projects) {
          return projects.map((project) => {
            project.route = {
              name: 'ProjectDetailOverview',
              params: {
                teamId: project.team,
                projectId: project.name,
              },
            }
            return project
          })
        },
      })
    },
  },
}
</script>
