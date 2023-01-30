<template>
  <div>
    <h1 class="sr-only">Homescreen</h1>
    <div class="mx-auto h-full max-w-4xl sm:px-5">
      <div class="px-2 pt-8 pb-6">
        <button
          @click="showCommandPalette"
          class="w-full rounded-md focus:outline-none focus:ring focus:ring-gray-300"
        >
          <Input
            :placeholder="searchPlaceholder"
            icon-left="search"
            class="cursor-pointer"
            :disabled="true"
          />
        </button>
      </div>
      <section class="space-y-2 px-2" v-if="$resources.pins.data?.length">
        <h2 class="text-2xl font-semibold text-gray-900">Pinned projects</h2>
        <Draggable
          class="grid grid-cols-3 gap-4"
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
                    class="opacity-0 transition-opacity group-hover:opacity-100"
                    appearance="minimal"
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
      <section class="mt-6 space-y-2">
        <button
          class="flex w-full items-center justify-between rounded-md px-2 py-1 hover:bg-gray-100"
          @click="recentProjects = !recentProjects"
        >
          <h2 class="text-2xl font-semibold text-gray-900">Recently visited</h2>
          <Motion :animate="{ rotate: recentProjects ? 90 : 0 }">
            <FeatherIcon name="chevron-right" class="h-4 w-4" />
          </Motion>
        </button>
        <div class="grid grid-cols-3 gap-4 px-2" v-show="recentProjects">
          <HomescreenProjectCard
            v-for="project in $resources.recentProjects.data"
            :key="project.name"
            :project="project"
          >
            <template #button>
              <Tooltip text="Pin this project">
                <Button
                  class="opacity-0 transition-opacity group-hover:opacity-100"
                  appearance="minimal"
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
  </div>
</template>
<script>
import Pin from '~icons/lucide/pin'
import Unpin from '~icons/lucide/pin-off'
import { getPlatform } from '@/utils'
import { showCommandPalette } from '@/components/CommandPalette.vue'
import Draggable from 'vuedraggable'
import HomescreenProjectCard from './HomeProjectCard.vue'
import { Motion } from '@motionone/vue'
import { Tooltip } from 'frappe-ui'
import { useLocalStorage } from '@/utils/composables'

export default {
  name: 'Homescreen',
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
          'creation',
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
    unreadCount() {
      if (!this.$resources.pins.data?.length) return
      return {
        url: 'gameplan.api.get_unread_items_by_project',
        params: {
          projects: this.$resources.pins.data.map((project) => project.name),
        },
        onSuccess(data) {
          this.$resources.pins.setData(
            this.$resources.pins.data.map((project) => {
              project.unreadCount = data[project.name]
              return project
            })
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
    let recentProjects = useLocalStorage('recentProjects', true)
    return {
      recentProjects,
      showCommandPalette,
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
    searchPlaceholder() {
      let platform = getPlatform()
      if (platform == 'mac') {
        return 'Jump to project or team (⌘+K)'
      }
      return 'Jump to project or team (Ctrl+K)'
    },
  },
}
</script>
