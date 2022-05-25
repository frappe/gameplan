<template>
  <div class="flex flex-col h-full">
    <header class="sticky top-0 z-10 h-12 px-4 py-3 bg-white border-b">
      <Breadcrumbs
        :breadcrumbs="[
          team?.doc && {
            title: team.doc.title,
            icon: team.doc.icon,
            route: {
              name: 'TeamPageHome',
              params: { teamId: team.doc.name },
            },
          },
          project && {
            title: project.title,
            icon: project.icon,
            route: task
              ? {
                  name: 'ProjectDetailTasks',
                  params: { projectId: project.name },
                }
              : undefined,
          },
          task?.doc && {
            title: task.doc.title,
          },
        ]"
      />
    </header>
    <div class="flex flex-col flex-1 h-full pt-8" v-if="project">
      <div class="border-b">
        <div class="px-6">
          <div class="flex items-start space-x-2">
            <IconPicker
              ref="projectIconPicker"
              v-model="project.icon"
              @update:modelValue="
                (icon) => $resources.project.setValue.submit({ icon })
              "
              :set-default="true"
            >
              <template v-slot="{ open }">
                <div
                  class="p-px leading-none rounded-md text-[30px] focus:outline-none"
                  :class="open ? 'bg-gray-200' : 'hover:bg-gray-100'"
                >
                  {{ project.icon || '' }}
                </div>
              </template>
            </IconPicker>
            <div>
              <div class="flex items-center space-x-2">
                <h1
                  class="text-6xl font-bold leading-8"
                  :title="`${Math.round(project.progress)}% complete`"
                >
                  {{ project.title }}
                </h1>
                <Dropdown
                  placement="left"
                  :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
                  :options="[
                    {
                      label: 'Delete this project',
                      icon: 'trash-2',
                      handler: () => (projectDeleteDialog = true),
                    },
                  ]"
                />
              </div>
              <Tabs :tabs="tabs" class="border-none" />
            </div>
          </div>
        </div>
      </div>

      <Dialog
        :options="{
          title: 'Delete project',
          message: 'Are you sure you want to delete this project?',
        }"
        v-model="projectDeleteDialog"
      >
        <template #actions>
          <Button
            appearance="danger"
            :loading="$resources.project.delete.loading"
            @click="
              () => {
                $resources.project.delete.submit().then(() => {
                  projectDeleteDialog = false
                  $getListResource(['Team Projects', team.doc.name])?.reload()
                  $router.push({
                    name: 'TeamPageHome',
                    params: { teamId: team.doc.name },
                  })
                })
              }
            "
          >
            Delete
          </Button>
          <Button @click="projectDeleteDialog = false">Cancel</Button>
        </template>
      </Dialog>

      <router-view class="flex-1" :project="$resources.project" />
    </div>
  </div>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import ProjectDetailTasks from './ProjectDetailTasks.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

export default {
  name: 'ProjectDetail',
  props: ['team', 'projectId'],
  components: {
    Dropdown,
    Spinner,
    Pie,
    ProjectDetailTasks,
    IconPicker,
    Links,
    Tabs,
    Breadcrumbs,
  },
  data() {
    return {
      projectDeleteDialog: false,
    }
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
          createSection: 'create_section',
          deleteSection: 'delete_section',
          updateTasksOrder: 'update_tasks_order',
        },
        transform(project) {
          project.sections.map((section) => {
            section.open = true
            section.tasks = []
          })
        },
      }
    },
  },
  computed: {
    project() {
      return this.$resources.project.doc
    },
    task() {
      let task = null
      if (this.$route.name === 'ProjectTaskDetail') {
        task = this.$getDocumentResource('Team Task', this.$route.params.taskId)
      }
      return task
    },
    tabs() {
      return [
        {
          name: 'Overview',
          icon: 'home',
          route: {
            name: 'ProjectDetailOverview',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
        {
          name: 'Tasks',
          icon: 'check-square',
          route: {
            name: 'ProjectDetailTasks',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
        {
          name: 'Updates',
          icon: 'server',
          route: {
            name: 'ProjectDetailUpdate',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
      ]
    },
  },
  methods: {
    tabLinkClasses($route, link) {
      let active = false
      if (link.route.name === $route.name) {
        active = true
      } else if ($route.fullPath === link.route) {
        active = true
      } else if ($route.matched.map((r) => r.name).includes(link.route.name)) {
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
