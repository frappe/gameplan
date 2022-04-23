<template>
  <div class="pb-40" v-if="$resources.project.doc">
    <div class="container pt-8 pb-4 mx-auto">
      <div>
        <router-link
          class="inline-flex items-center p-2 mb-2 space-x-2 text-base rounded-md hover:bg-gray-50"
          :to="{
            name: 'TeamPageHome',
            params: { teamId: $resources.project.doc.team },
          }"
        >
          <FeatherIcon name="arrow-left" class="w-4" />
          <span class="text-gray-800">
            back to {{ $resources.project.doc.team }}
          </span>
        </router-link>
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-2">
            <IconPicker
              ref="projectIconPicker"
              v-model="project.icon"
              @update:modelValue="
                (icon) => $resources.project.setValue.submit({ icon })
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
                        loading: $resources.project.delete.loading,
                        handler: ({ close }) => {
                          $resources.project.delete.submit().then(() => {
                            close()
                            this.$router.push(`/${this.team.name}`)
                          })
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

    <router-view :project="$resources.project" />
  </div>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import ProjectDetailTasks from './ProjectDetailTasks.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'

export default {
  name: 'ProjectDetail',
  props: ['teamId', 'team', 'projectId'],
  components: {
    Dropdown,
    Spinner,
    Pie,
    ProjectDetailTasks,
    IconPicker,
    Links,
  },
  resources: {
    project() {
      return {
        type: 'document',
        doctype: 'Team Project',
        name: this.projectId,
        whitelistedMethods: {
          removeMember: 'remove_member',
          inviteMembers: 'invite_members',
          addAttachment: 'add_attachment',
        },
        postprocess(project) {
          if (!project.icon) {
            this.$nextTick(() => this.$refs.projectIconPicker.setRandom())
          }
          project.task_states.map((task_state) => {
            task_state.open = true
          })
        },
      }
    },
  },
  computed: {
    project() {
      return this.$resources.project.doc
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
