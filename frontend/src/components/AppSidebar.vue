<template>
  <div
    class="absolute right-0 z-10 h-full w-1 cursor-col-resize bg-gray-300 opacity-0 transition-opacity hover:opacity-100"
    :class="{ 'opacity-100': sidebarResizing }"
    @mousedown="startResize"
  />
  <div
    v-show="sidebarResizing"
    class="fixed m-2 rounded-md bg-gray-800 px-2 py-1 text-base text-white"
    :style="{ left: sidebarWidth + 'px' }"
  >
    {{ sidebarWidth }}
  </div>

  <div
    class="inline-flex h-full flex-1 flex-col overflow-auto bg-gray-100 pb-40"
    :style="{ width: `${sidebarWidth}px` }"
  >
    <div class="flex w-full items-center justify-between px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="px-2">
        <Links
          :links="navigation"
          class="flex items-center rounded-md px-2 py-2 font-medium"
          active="bg-white shadow-sm text-gray-900"
          inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        >
          <template v-slot="{ link }">
            <div class="flex w-full items-center space-x-2">
              <span class="grid h-5 w-5 place-items-center">
                <FeatherIcon :name="link.icon" class="h-4 w-4" />
              </span>
              <span class="text-base">{{ link.name }}</span>
              <span
                v-if="
                  link.unreadNotifications && link.unreadNotifications.data > 0
                "
                class="!ml-auto block text-sm text-gray-800"
              >
                {{ link.unreadNotifications.data }}
              </span>
            </div>
          </template>
        </Links>
      </nav>
      <div class="mt-6 flex items-center justify-between px-3">
        <h3 class="text-sm font-semibold text-gray-700">Teams</h3>
        <Button
          icon="plus"
          label="Create Team"
          @click="showAddTeamDialog = true"
        />
      </div>
      <nav class="mt-1 px-2">
        <div v-for="team in activeTeams" :key="team.name">
          <Link
            :link="team"
            class="flex items-center rounded-md px-2 py-2 font-medium"
          >
            <button
              @click.prevent="
                () => {
                  team.open = !team.open
                }
              "
              class="mr-2 grid h-5 w-5 place-items-center rounded hover:bg-gray-200"
            >
              <Motion :animate="{ rotate: team.open ? 90 : 0 }">
                <FeatherIcon name="chevron-right" class="h-4 w-4" />
              </Motion>
            </button>
            <span class="inline-flex items-center space-x-2">
              <span class="flex h-5 w-5 items-center justify-center text-xl">
                {{ team.icon }}
              </span>
              <span class="text-base">{{ team.title }}</span>
            </span>
          </Link>
          <div v-show="team.open">
            <Links
              :links="teamProjects(team.name)"
              class="mt-0.5 flex items-center rounded-md py-1.5 pl-12 pr-2 font-medium"
              active="bg-white shadow-sm text-gray-900"
              inactive="text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            >
              <template v-slot="{ link: project }">
                <span class="inline-flex items-center space-x-2">
                  <span
                    class="flex h-5 w-5 items-center justify-center text-xl"
                  >
                    {{ project.icon }}
                  </span>
                  <span class="text-base">{{ project.title }}</span>
                  <FeatherIcon
                    v-if="project.is_private"
                    name="lock"
                    class="h-3 w-3"
                  />
                </span>
              </template>
            </Links>
          </div>
        </div>
      </nav>
      <div
        v-if="teams.fetched && !activeTeams.length"
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
          $router.push(`/${team.name}`)
        }
      "
    />
  </div>
</template>
<script>
import { Tooltip, FeatherIcon } from 'frappe-ui'
import Links from './Links.vue'
import Link from './Link.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import { activeTeams, teams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { unreadNotifications } from '@/data/notifications'
import UserDropdown from './UserDropdown.vue'
import { Motion } from 'motion/vue'

export default {
  name: 'AppSidebar',
  components: {
    AddTeamDialog,
    Links,
    Link,
    UserDropdown,
    Tooltip,
    FeatherIcon,
    Motion,
  },
  data() {
    return {
      sidebarOpen: true,
      sidebarWidth: 256,
      sidebarResizing: false,

      showAddTeamDialog: false,
      teams,
    }
  },
  mounted() {
    this.$socket.on('gameplan:new_notification', () => {
      unreadNotifications.reload()
    })
    let sidebarWidth = parseInt(localStorage.getItem('sidebarWidth') || 256)
    this.sidebarWidth = sidebarWidth
  },
  computed: {
    navigation() {
      return [
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
          isActive: /People|PersonProfile/g.test(this.$route.name),
        },
        {
          name: 'Search',
          icon: 'search',
          route: {
            name: 'Search',
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
      ]
    },
    activeTeams() {
      return activeTeams.value.map((team) => {
        team.class = function ($route, link) {
          if (
            ['Team', 'TeamHome', 'TeamOverview', 'TeamProjects'].includes(
              $route.name
            ) &&
            $route.params.teamId === link.route.params.teamId
          ) {
            return 'bg-white shadow-sm text-gray-900'
          }
          return 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
        }
        return team
      })
    },
  },
  methods: {
    teamProjects(teamName) {
      return getTeamProjects(teamName).filter((project) => !project.archived_at)
    },
    startResize() {
      document.addEventListener('mousemove', this.resize)
      document.addEventListener('mouseup', () => {
        document.body.classList.remove('select-none')
        document.body.classList.remove('cursor-col-resize')
        localStorage.setItem('sidebarWidth', this.sidebarWidth)
        this.sidebarResizing = false
        document.removeEventListener('mousemove', this.resize)
      })
    },
    resize(e) {
      this.sidebarResizing = true
      document.body.classList.add('select-none')
      document.body.classList.add('cursor-col-resize')
      this.sidebarWidth = e.clientX

      // snap to 256
      let range = [256 - 10, 256 + 10]
      if (this.sidebarWidth > range[0] && this.sidebarWidth < range[1]) {
        this.sidebarWidth = 256
      }

      if (this.sidebarWidth < 12 * 16) {
        this.sidebarWidth = 12 * 16
      }
      if (this.sidebarWidth > 24 * 16) {
        this.sidebarWidth = 24 * 16
      }
    },
  },
}
</script>
