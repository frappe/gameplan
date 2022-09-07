<template>
  <div class="flex flex-1 flex-col py-6">
    <div class="flex-1">
      <nav class="space-y-1 px-2">
        <Links
          :links="navigation"
          class="flex items-center rounded-md px-2 py-2 font-medium"
          active="bg-gray-200 text-gray-900"
          inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        >
          <template v-slot="{ link }">
            <div class="flex w-full items-center space-x-2">
              <span class="grid h-5 w-5 place-items-center">
                <FeatherIcon :name="link.icon" class="h-4 w-4" />
              </span>
              <span class="text-lg">{{ link.name }}</span>
              <span
                v-if="
                  link.unreadNotifications && link.unreadNotifications.data > 0
                "
                class="!ml-auto block rounded bg-red-500 px-1 text-sm text-white"
              >
                {{ link.unreadNotifications.data }}
              </span>
            </div>
          </template>
        </Links>
      </nav>
      <div class="mt-6 flex items-center justify-between px-3">
        <h3
          class="text-xs font-semibold uppercase tracking-wider text-gray-500"
        >
          Your Teams
        </h3>
        <Button icon="plus" @click="showAddTeamDialog = true">
          Create Team
        </Button>
      </div>
      <nav class="mt-1 space-y-1 px-2">
        <div v-for="team in teams.data" :key="team.name">
          <Link
            :link="team"
            class="flex items-center rounded-md px-2 py-2 font-medium"
            exact-active="bg-gray-200 text-gray-900"
            inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          >
            <button
              @click.prevent="
                () => {
                  team.open = !team.open
                }
              "
              class="mr-2 grid h-5 w-5 place-items-center rounded hover:bg-gray-200"
            >
              <FeatherIcon
                :name="team.open ? 'chevron-down' : 'chevron-right'"
                class="h-4 w-4"
              />
            </button>
            <span class="inline-flex items-center space-x-2">
              <span class="flex h-5 w-5 items-center justify-center text-xl">
                {{ team.icon }}
              </span>
              <span class="text-lg">{{ team.title }}</span>
            </span>
          </Link>
          <div v-show="team.open">
            <Links
              :links="getTeamProjects(team.name)"
              class="mt-0.5 flex items-center rounded-md py-1.5 pl-12 pr-2 font-medium"
              active="bg-gray-200 text-gray-900"
              inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <template v-slot="{ link }">
                <span class="inline-flex items-center space-x-2">
                  <span
                    class="flex h-5 w-5 items-center justify-center text-xl"
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
import Links from './Links.vue'
import Link from './Link.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import { teams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { unreadNotifications } from '@/data/notifications'

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
        {
          name: 'Notifications',
          icon: 'bell',
          route: {
            name: 'Notifications',
          },
          unreadNotifications,
        },
      ],
      showAddTeamDialog: false,
      teams,
    }
  },
  mounted() {
    this.$socket.on('gameplan:new_notification', () => {
      unreadNotifications.reload()
    })
  },
  methods: {
    getTeamProjects,
  },
}
</script>
