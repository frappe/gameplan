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
    <div class="flex flex-col px-2 py-2">
      <UserDropdown />
    </div>
    <div class="flex-1">
      <nav class="space-y-0.5 px-2">
        <Links
          :links="navigation"
          class="flex items-center rounded px-2 py-1 text-gray-800 transition"
          active="bg-white shadow-sm"
          inactive="hover:bg-gray-100"
        >
          <template v-slot="{ link }">
            <div class="flex w-full items-center space-x-2">
              <span class="grid h-5 w-6 place-items-center">
                <component :is="link.icon" class="h-4 w-4 text-gray-700" />
              </span>
              <span class="text-sm">{{ link.name }}</span>
              <span
                v-if="link.count"
                class="!ml-auto block text-xs text-gray-600"
              >
                {{ link.count }}
              </span>
            </div>
          </template>
        </Links>
        <button
          v-if="$user().isNotGuest"
          class="flex w-full items-center rounded px-2 py-1 text-gray-800"
          :class="[
            /Search/.test($route.name)
              ? 'bg-white shadow-sm'
              : 'hover:bg-gray-100',
          ]"
          @click="showCommandPalette"
        >
          <div class="flex w-full items-center">
            <span class="grid h-5 w-6 place-items-center">
              <LucideSearch class="h-4 w-4 text-gray-700" />
            </span>
            <span class="ml-2 text-sm">Search</span>
            <span class="ml-auto text-sm text-gray-500">
              <template v-if="$platform === 'mac'">⌘K</template>
              <template v-else>Ctrl+K</template>
            </span>
          </div>
        </button>
      </nav>
      <div class="mt-6 flex items-center justify-between px-3">
        <h3 class="text-sm font-medium text-gray-600">Teams</h3>
        <Button
          label="Create Team"
          variant="ghost"
          @click="showAddTeamDialog = true"
        >
          <template #icon><LucidePlus class="h-4 w-4" /></template>
        </Button>
      </div>
      <nav class="mt-1 space-y-0.5 px-2">
        <div v-for="team in activeTeams" :key="team.name">
          <Link
            :link="team"
            class="flex items-center rounded px-2 py-1 transition"
          >
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
              <span class="ml-2 text-sm">{{ team.title }}</span>
              <LucideLock v-if="team.is_private" class="ml-2 h-3 w-3" />
              <div class="ml-auto">
                <Tooltip
                  v-if="team.unread"
                  :text="`${team.unread} unread posts`"
                >
                  <span class="text-xs text-gray-600">{{ team.unread }}</span>
                </Tooltip>
              </div>
            </div>
          </Link>
          <div class="mb-2 mt-0.5 space-y-0.5 pl-7" v-show="team.open">
            <Link
              :key="project.name"
              v-for="project in teamProjects(team.name)"
              :link="project"
              :ref="($comp) => setProjectRef($comp, project)"
              class="flex h-7 items-center rounded-md px-2 text-gray-800 transition"
              active="bg-white shadow-sm"
              inactive="hover:bg-gray-100"
            >
              <template v-slot="{ link: project }">
                <span class="inline-flex items-center space-x-2">
                  <span class="text-sm">{{ project.title }}</span>
                  <LucideLock v-if="project.is_private" class="h-3 w-3" />
                </span>
              </template>
            </Link>
            <div
              class="flex h-7 items-center px-2 text-sm text-gray-600"
              v-if="teamProjects(team.name).length === 0"
            >
              No projects
            </div>
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
import { Tooltip } from 'frappe-ui'
import Links from './Links.vue'
import Link from './Link.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import UserDropdown from './UserDropdown.vue'
import ChevronTriangle from './icons/ChevronTriangle.vue'
import { activeTeams, teams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { unreadNotifications } from '@/data/notifications'
import { showCommandPalette } from '@/components/CommandPalette/CommandPalette.vue'
import LucideUsers2 from '~icons/lucide/users-2'
import LucideInbox from '~icons/lucide/inbox'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'
import LucideFiles from '~icons/lucide/files'

export default {
  name: 'AppSidebar',
  components: {
    AddTeamDialog,
    Links,
    Link,
    UserDropdown,
    Tooltip,
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
          name: 'Discussions',
          icon: LucideNewspaper,
          route: {
            name: 'Discussions',
          },
        },
        {
          name: 'My Tasks',
          icon: LucideListTodo,
          route: {
            name: 'MyTasks',
          },
          isActive: /MyTasks|Task/g.test(this.$route.name),
        },
        {
          name: 'My Pages',
          icon: LucideFiles,
          route: {
            name: 'MyPages',
          },
          isActive: /MyPages|Page/g.test(this.$route.name),
        },
        {
          name: 'People',
          icon: LucideUsers2,
          route: {
            name: 'People',
          },
          isActive: /People|PersonProfile/g.test(this.$route.name),
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Notifications',
          icon: LucideInbox,
          route: {
            name: 'Notifications',
          },
          count: unreadNotifications.data || 0,
        },
      ].filter((nav) => (nav.condition ? nav.condition() : true))
    },
    activeTeams() {
      return activeTeams.value.map((team) => {
        team.class = function ($route, link) {
          if (
            ['TeamLayout', 'Team', 'TeamOverview'].includes($route.name) &&
            $route.params.teamId === link.route.params.teamId
          ) {
            return 'bg-white shadow-sm text-gray-800'
          }
          return 'text-gray-800 hover:bg-gray-100'
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
    showCommandPalette,
  },
}
</script>
