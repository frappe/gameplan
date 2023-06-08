<template>
  <div class="mx-auto mt-5 h-full max-w-4xl pb-20 sm:px-5">
    <section class="mb-6 space-y-2 px-4 lg:px-2">
      <h2 class="text-lg font-semibold text-gray-900">Pinned</h2>
      <p
        class="text-base text-gray-600"
        v-if="$resources.pins.data?.length === 0"
      >
        You haven't pinned any projects. Start by pinning a project from the
        list below.
      </p>
      <Draggable
        class="grid grid-cols-1 gap-4 lg:grid-cols-3"
        v-model="$resources.pins.data"
        group="pins"
        item-key="name"
        @end="updatePinOrders"
        :animation="200"
      >
        <template #item="{ element: project }">
          <HomescreenProjectCard :project="project">
            <template #button>
              <Tooltip text="Unpin this project">
                <Button
                  variant="ghost"
                  @click.prevent="unpinProject(project.pinId)"
                  :loading="
                    $resources.pins.delete.loading &&
                    $resources.pins.delete.params.name == project.name
                  "
                >
                  <template #icon>
                    <Unpin class="h-4 w-4" stroke-width="1.5" />
                  </template>
                </Button>
              </Tooltip>
            </template>
          </HomescreenProjectCard>
        </template>
      </Draggable>
    </section>
    <section class="mt-6" v-if="$resources.activeProjects.data?.length">
      <button
        class="flex w-full items-center justify-between rounded-md px-4 py-2 hover:bg-gray-100 lg:px-2"
        @click="activeProjects = !activeProjects"
      >
        <h2 class="text-lg font-semibold text-gray-900">Active</h2>
        <Motion :animate="{ rotate: activeProjects ? 90 : 0 }">
          <FeatherIcon name="chevron-right" class="h-4 w-4" />
        </Motion>
      </button>

      <div
        class="mb-6 mt-2 grid grid-cols-1 gap-4 px-4 lg:grid-cols-3 lg:px-2"
        v-show="activeProjects"
      >
        <HomescreenProjectCard
          v-for="project in $resources.activeProjects.data"
          :key="project.name"
          :project="project"
        >
          <template #button>
            <Tooltip text="Pin this project">
              <Button
                variant="ghost"
                @click.prevent="pinProject(project.name)"
                :loading="
                  $resources.pins.insert.loading &&
                  $resources.pins.insert.params.doc.project == project.name
                "
              >
                <template #icon>
                  <Pin class="h-4 w-4" stroke-width="1.5" />
                </template>
              </Button>
            </Tooltip>
          </template>
        </HomescreenProjectCard>
      </div>
    </section>
    <section
      class="space-y-2 border-t border-transparent"
      :class="{
        'border-gray-200':
          !activeProjects && $resources.activeProjects.data?.length,
      }"
    >
      <button
        class="flex w-full items-center justify-between rounded-md px-4 py-2 hover:bg-gray-100 lg:px-2"
        @click="recentProjects = !recentProjects"
      >
        <h2 class="text-lg font-semibold text-gray-900">Recent</h2>

        <Motion :animate="{ rotate: recentProjects ? 90 : 0 }">
          <FeatherIcon name="chevron-right" class="h-4 w-4" />
        </Motion>
      </button>
      <div
        class="grid grid-cols-1 gap-4 px-4 lg:grid-cols-3 lg:px-2"
        v-show="recentProjects"
      >
        <HomescreenProjectCard
          v-for="project in $resources.recentProjects.data"
          :key="project.name"
          :project="project"
        >
          <template #button>
            <Tooltip text="Pin this project">
              <Button
                variant="ghost"
                @click.prevent="pinProject(project.name)"
                :loading="
                  $resources.pins.insert.loading &&
                  $resources.pins.insert.params.doc.project == project.name
                "
              >
                <template #icon>
                  <Pin class="h-4 w-4" stroke-width="1.5" />
                </template>
              </Button>
            </Tooltip>
          </template>
        </HomescreenProjectCard>
      </div>
    </section>
  </div>
</template>
<script>
import Pin from '~icons/lucide/pin'
import Unpin from '~icons/lucide/pin-off'
import Draggable from 'vuedraggable'
import HomescreenProjectCard from './HomeProjectCard.vue'
import { Motion } from '@motionone/vue'
import { Tooltip } from 'frappe-ui'
import { useLocalStorage } from '@/utils/composables'

export default {
  name: 'HomeProjects',
  components: {
    Pin,
    Unpin,
    Draggable,
    HomescreenProjectCard,
    Motion,
    Tooltip,
  },
  resources: {
    pins() {
      return {
        type: 'list',
        cache: 'PinnedProjects',
        doctype: 'GP Pinned Project',
        fields: [
          'name as pinId',
          'project as name',
          'project.icon as icon',
          'project.title as project_title',
          'team',
          'team.title as team_title',
          'creation as timestamp',
        ],
        orderBy: 'order asc, creation asc',
        auto: true,
      }
    },
    recentProjects() {
      return {
        url: 'gameplan.api.recent_projects',
        cache: 'RecentProjects',
        auto: true,
      }
    },
    activeProjects() {
      return {
        url: 'gameplan.api.active_projects',
        cache: 'ActiveProjects',
        auto: true,
      }
    },
    unreadCount() {
      if (!this.projectNames.length) return
      return {
        url: 'gameplan.api.get_unread_items_by_project',
        params: {
          projects: this.projectNames,
        },
        onSuccess(data) {
          function setUnreadCount(project) {
            let unreadCount = data[project.name]
            if (unreadCount != null) {
              project.unreadCount = unreadCount
            }
            return project
          }
          this.$resources.pins.setData(
            this.$resources.pins.data.map(setUnreadCount)
          )
          this.$resources.recentProjects.setData(
            this.$resources.recentProjects.data.map(setUnreadCount)
          )
          this.$resources.activeProjects.setData(
            this.$resources.activeProjects.data.map(setUnreadCount)
          )
        },
        auto: true,
      }
    },
    bulkUpdatePinOrder() {
      return {
        url: 'frappe.client.bulk_update',
      }
    },
  },
  setup() {
    let recentProjects = useLocalStorage('isRecentProjectsShown', true)
    let activeProjects = useLocalStorage('isActiveProjectsShown', true)
    return {
      recentProjects,
      activeProjects,
    }
  },
  methods: {
    pinProject(project) {
      this.$resources.pins.insert.submit(
        { project },
        {
          onSuccess() {
            this.$resources.recentProjects.reload()
          },
        }
      )
    },
    unpinProject(name) {
      this.$resources.pins.delete.submit(name, {
        onSuccess() {
          this.$resources.recentProjects.reload()
        },
      })
    },
    updatePinOrders() {
      let docs = this.$resources.pins.data.map((project, index) => ({
        doctype: 'GP Pinned Project',
        docname: project.pinId,
        order: index + 1,
      }))
      this.$resources.bulkUpdatePinOrder.submit({ docs: JSON.stringify(docs) })
    },
  },
  computed: {
    projectNames() {
      let names = [
        ...(this.$resources.pins.data || []),
        ...(this.$resources.activeProjects.data || []),
        ...(this.$resources.recentProjects.data || []),
      ].map((project) => project.name)
      // unique names
      return [...new Set(names)]
    },
  },
}
</script>
