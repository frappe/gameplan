<template>
  <div class="pb-40" v-if="$resources.project.data">
    <div class="container pt-8 pb-4 mx-auto">
      <div>
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-2">
            <ProjectIconPicker
              ref="projectIconPicker"
              v-model="project.icon"
              @update:modelValue="
                (icon) =>
                  $resources.updateProject.submit({
                    doctype: 'Team Project',
                    name: project.name,
                    fieldname: {
                      icon,
                    },
                  })
              "
            />
            <h1
              class="text-6xl font-bold"
              :title="`${Math.round(project.progress)}% complete`"
            >
              {{ project.title }}
            </h1>
          </div>
          <Dropdown
            placement="left"
            :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
            :options="[
              {
                label: 'Delete this project',
                icon: 'trash-2',
                handler: () =>
                  $dialog({
                    title: 'Delete project',
                    message: 'Are you sure you want to delete this project?',
                    actions: [
                      {
                        label: 'Delete',
                        appearance: 'danger',
                        loading: $resources.deleteProject.loading,
                        handler: ({ close }) => {
                          $resources.deleteProject
                            .submit({
                              doctype: 'Team Project',
                              name: project.name,
                            })
                            .then(() => close())
                        },
                      },
                      {
                        label: 'Cancel',
                        handler: 'cancel',
                      },
                    ],
                  }),
              },
            ]"
          />
        </div>
        <p class="text-sm text-gray-500">
          created {{ $dayjs(project.creation).fromNow() }}
        </p>
      </div>
    </div>

    <div class="border-b">
      <div class="container mx-auto">
        <div class="mt-2">
          <div class="sm:hidden">
            <label for="tabs" class="sr-only">Select a tab</label>
            <!-- Use an "onChange" listener to redirect the user to the selected tab URL. -->
            <select
              id="tabs"
              name="tabs"
              class="block w-full py-2 pl-3 pr-10 text-base border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              @change="$router.push($event.target.value)"
            >
              <option
                v-for="tab in tabs"
                :key="tab.name"
                :selected="$route.fullPath === tab.route"
                :value="tab.route"
              >
                {{ tab.name }}
              </option>
            </select>
          </div>
          <div class="hidden sm:block">
            <div>
              <nav class="flex -mb-px space-x-8" aria-label="Tabs">
                <Links
                  :links="tabs"
                  class="px-1 py-2 text-sm font-medium border-b-2 whitespace-nowrap"
                />
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>

    <router-view :project="$resources.project.data" />
  </div>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import ProjectDetailTasks from './ProjectDetailTasks.vue'
import ProjectIconPicker from '@/components/ProjectIconPicker.vue'
import Links from '@/components/Links.vue'

export default {
  name: 'ProjectDetail',
  props: ['teamId', 'team', 'projectId'],
  components: {
    Dropdown,
    Spinner,
    Pie,
    ProjectDetailTasks,
    ProjectIconPicker,
    Links,
  },
  resources: {
    project() {
      return {
        method: 'frappe.client.get',
        cache: ['Team Project', this.projectId],
        params: {
          doctype: 'Team Project',
          name: this.projectId,
        },
        auto: true,
        onSuccess(project) {
          if (!project.icon) {
            this.$nextTick(() => this.$refs.projectIconPicker.setRandom())
          }
          project.task_states.map((task_state) => {
            task_state.open = true
          })
        },
      }
    },
    updateProject() {
      return {
        method: 'frappe.client.set_value',
      }
    },
    deleteProject() {
      return {
        method: 'frappe.client.delete',
        onSuccess() {
          this.$router.push(`/${this.team.name}`)
        },
      }
    },
  },
  computed: {
    project() {
      return this.$resources.project.data ? this.$resources.project.data : null
    },
    tabs() {
      return [
        {
          name: 'Overview',
          route: `/${this.team.name}/projects/${this.projectId}`,
          class: this.tabLinkClasses,
        },
        {
          name: 'Tasks',
          route: `/${this.team.name}/projects/${this.projectId}/tasks`,
          class: this.tabLinkClasses,
        },
      ]
    },
  },
  methods: {
    tabLinkClasses($route, link) {
      let active = false
      if ($route.fullPath === link.route) {
        active = true
      }
      if (link.name != 'Overview' && $route.fullPath.startsWith(link.route)) {
        active = true
      }
      if (active) {
        return 'border-blue-500 text-blue-600'
      }
      return 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
    },
  },
}
</script>
