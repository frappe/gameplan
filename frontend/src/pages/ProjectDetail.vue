<template>
  <div class="flex flex-col h-full">
    <header class="sticky top-0 z-10 bg-white">
      <div class="h-12 px-4 py-3 border-b">
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
      </div>
      <div class="pt-8 border-b" v-if="project">
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
                      label: 'Move to another team',
                      icon: 'log-out',
                      handler: () => (projectMoveDialog.show = true),
                    },
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
      <Dialog
        :options="{
          title: 'Move project to another team',
        }"
        @close="
          () => {
            projectMoveDialog.team = null
            $resources.project.moveToTeam.reset()
          }
        "
        v-model="projectMoveDialog.show"
      >
        <template #body-content>
          <Autocomplete
            :options="
              $getListResource('Sidebar Teams')
                .data.filter((d) => d.name != team.doc.name)
                .map((d) => ({
                  label: d.title,
                  value: d.name,
                }))
            "
            v-model="projectMoveDialog.team"
          />
          <ErrorMessage
            class="mt-2"
            :message="$resources.project.moveToTeam.error"
          />
        </template>
        <template #actions>
          <Button
            appearance="primary"
            :loading="$resources.project.moveToTeam.loading"
            @click="
              () => {
                $resources.project.moveToTeam.submit(
                  { team: projectMoveDialog.team?.value },
                  {
                    validate() {
                      if (!projectMoveDialog.team?.value) {
                        return 'Team is required to move this project'
                      }
                    },
                    onSuccess() {
                      onProjectMove()
                    },
                  }
                )
              }
            "
          >
            {{
              projectMoveDialog.team
                ? `Move to ${projectMoveDialog.team.label}`
                : 'Move'
            }}
          </Button>
          <Button @click="projectMoveDialog.show = false">Cancel</Button>
        </template>
      </Dialog>
    </header>
    <div class="flex flex-col flex-1 h-full min-h-0" v-if="project">
      <router-view class="flex-1 h-full" :project="$resources.project" />
    </div>
  </div>
</template>
<script>
import { Autocomplete, Dropdown, Spinner } from 'frappe-ui'
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
    Autocomplete,
  },
  data() {
    return {
      projectDeleteDialog: false,
      projectMoveDialog: { show: false, team: null },
    }
  },
  mounted() {
    this.$getListResource('Sidebar Teams').setData((teams) => {
      for (let team of teams) {
        if (team.name === this.team.doc.name) {
          team.open = true
          if (!team.projects.data) {
            team.projects.fetch()
          }
        }
      }
      return teams
    })
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
          moveToTeam: 'move_to_team',
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
          name: 'Readme',
          // icon: 'home',
          route: {
            name: 'ProjectDetailOverview',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
        {
          name: 'Discussions',
          // icon: 'server',
          route: {
            name: 'ProjectDetailUpdate',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
        {
          name: 'Tasks',
          // icon: 'check-square',
          route: {
            name: 'ProjectDetailTasks',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          class: this.tabLinkClasses,
        },
      ]
    },
  },
  methods: {
    onProjectMove() {
      this.projectMoveDialog.show = false
      this.$getListResource(['Team Projects', this.team.doc.name])?.reload()
      let teams = this.$getListResource('Sidebar Teams')
      for (let team of teams.data) {
        if (
          [this.team.doc.name, this.projectMoveDialog.team.value].includes(
            team.name
          )
        ) {
          team.projects.reload()
          if (this.projectMoveDialog.team.value === team.name) {
            team.open = true
          }
        }
      }
      this.$router.push({
        name: 'ProjectDetailOverview',
        params: {
          teamId: this.projectMoveDialog.team.value,
          projectId: this.projectId,
        },
      })
      this.projectMoveDialog.team = null
      this.$resources.project.moveToTeam.reset()
    },
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
  pageMeta() {
    return {
      title: `${this.project.title} - ${this.team.doc.title}`,
      emoji: this.project.icon,
    }
  },
}
</script>
