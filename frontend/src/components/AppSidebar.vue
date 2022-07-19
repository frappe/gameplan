<template>
  <div class="flex flex-col flex-1 py-6 overflow-y-auto">
    <div class="flex-1">
      <nav class="px-2 space-y-1">
        <Links
          :links="navigation"
          class="flex items-center px-2 py-2 font-medium rounded-md"
          active="bg-gray-200 text-gray-900"
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
      <div class="flex items-center justify-between px-3 mt-6">
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
        <div v-for="team in teams.data" :key="team.name">
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
              <span class="flex items-center justify-center w-5 h-5 text-xl">
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
        v-if="teams.fetched && !teams.data.length"
        class="px-3 py-2 text-sm text-gray-500"
      >
        No teams
      </div>
    </div>
    <AddTeamDialog
      v-model:show="showAddTeamDialog"
      @success="
        (team) => {
          showAddTeamDialog = false
          teams.fetch()
          $router.push(`/${team.name}`)
        }
      "
    />
  </div>
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
import { teams } from '@/resources/teams'

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
      ],
      showAddTeamDialog: false,
      teams,
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
