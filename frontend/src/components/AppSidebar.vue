<template>
  <div
    class="absolute right-0 z-10 h-full w-1 cursor-col-resize bg-gray-300 opacity-0 transition-opacity hover:opacity-100"
    :class="{ 'opacity-100': sidebarResizing }"
    @mousedown="startResize"
  />
  <div
    v-show="sidebarResizing"
    class="fixed z-20 mt-3 -translate-x-[130%] rounded-md bg-gray-800 px-2 py-1 text-base text-white"
    :style="{ left: sidebarWidth + 'px' }"
  >
    {{ sidebarWidth }}
  </div>

  <div
    class="inline-flex h-full flex-1 flex-col overflow-auto border-r bg-gray-50 pb-40"
    :style="{ width: `${sidebarWidth}px` }"
  >
    <div class="flex w-full items-center justify-between px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="space-y-0.5 px-2">
        <Links
          :links="navigation"
          class="flex items-center rounded-lg px-2 py-1"
          active="bg-gray-200 text-gray-900"
          inactive="text-gray-700 hover:bg-gray-100 hover:text-gray-900"
        >
          <template v-slot="{ link }">
            <div class="flex w-full items-center space-x-3">
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
          appearance="minimal"
          @click="showAddTeamDialog = true"
        />
      </div>
      <nav class="mt-1 space-y-0.5 px-2">
        <div v-for="team in activeTeams" :key="team.name">
          <Link :link="team" class="flex items-center rounded-lg px-2 py-1">
            <button
              @click.prevent="
                () => {
                  team.open = !team.open
                }
              "
              class="mr-1.5 grid h-4 w-4 place-items-center rounded hover:bg-gray-200"
            >
              <Motion :animate="{ rotate: team.open ? 90 : 0 }">
                <ChevronTriangle class="h-3 w-3 text-gray-500" />
              </Motion>
            </button>
            <div class="flex w-full items-center">
              <span class="flex h-5 w-5 items-center justify-center text-xl">
                {{ team.icon }}
              </span>
              <span class="ml-2 text-base">{{ team.title }}</span>
              <FeatherIcon
                v-if="team.is_private"
                name="lock"
                class="ml-2 h-3 w-3"
              />
              <div class="ml-auto">
                <Tooltip
                  v-if="team.unread"
                  :text="`${team.unread} unread posts`"
                >
                  <span class="text-sm text-gray-600">{{ team.unread }}</span>
                </Tooltip>
              </div>
            </div>
          </Link>
          <div class="mb-2 mt-0.5 space-y-0.5" v-show="team.open">
            <Link
              :key="project.name"
              v-for="project in teamProjects(team.name)"
              :link="project"
              :ref="($comp) => setProjectRef($comp, project)"
              class="flex items-center rounded-md py-1 pl-12 pr-2"
              active="bg-gray-200 text-gray-900"
              inactive="text-gray-700 hover:bg-gray-100 hover:text-gray-900"
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
            </Link>
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
          $router.push({
            name: 'TeamOverview',
            params: { teamId: team.name },
          })
        }
      "
    />
  </div>
</template>
<script>
import { Motion } from 'motion/vue'
import { Tooltip, FeatherIcon } from 'frappe-ui'
import Links from './Links.vue'
import Link from './Link.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import UserDropdown from './UserDropdown.vue'
import ChevronTriangle from './icons/ChevronTriangle.vue'
import { activeTeams, teams, unreadItems } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { unreadNotifications } from '@/data/notifications'

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
    ChevronTriangle,
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
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Search',
          icon: 'search',
          route: {
            name: 'Search',
          },
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Notifications',
          icon: 'bell',
          route: {
            name: 'Notifications',
          },
          unreadNotifications,
        },
      ].filter((nav) => (nav.condition ? nav.condition() : true))
    },
    activeTeams() {
      return activeTeams.value.map((team) => {
        team.class = function ($route, link) {
          if (
            ['TeamLayout', 'Team', 'TeamOverview', 'TeamProjects'].includes(
              $route.name
            ) &&
            $route.params.teamId === link.route.params.teamId
          ) {
            return 'bg-gray-200 text-gray-900'
          }
          return 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
        }
        return team
      })
    },
  },
  methods: {
    teamProjects(teamName) {
      return getTeamProjects(teamName)
        .filter((project) => !project.archived_at)
        .map((project) => {
          if (
            this.$route.name === 'ProjectDiscussion' &&
            this.$route.params.projectId == project.name
          ) {
            project.isActive = true
            this.scrollProjectIntoView(project)
          } else {
            project.isActive = false
          }
          return project
        })
    },
    setProjectRef($comp, project) {
      this.$projectRefs = this.$projectRefs || {}
      if ($comp) {
        this.$projectRefs[project.name] = $comp.getRef()
      }
    },
    async scrollProjectIntoView(project) {
      await this.$nextTick()
      const $el = this.$projectRefs[project.name]
      if ($el) {
        $el.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'nearest',
        })
      }
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
