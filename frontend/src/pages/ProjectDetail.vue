<template>
  <div class="flex h-full flex-col pt-8">
    <header>
      <div class="border-b" v-if="project">
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
                class="rounded-md p-px text-[30px] leading-none focus:outline-none"
                :class="open ? 'bg-gray-200' : 'hover:bg-gray-100'"
              >
                {{ project.icon || '' }}
              </div>
            </template>
          </IconPicker>
          <div>
            <div class="flex items-center space-x-2">
              <Popover ref="editTitlePopup" :hideOnBlur="false">
                <template #target>
                  <h1
                    class="text-6xl font-bold leading-8"
                    :title="`${Math.round(project.progress)}% complete`"
                  >
                    {{ project.title }}
                  </h1>
                </template>
                <template #body-main>
                  <div class="p-2">
                    <div class="flex items-end space-x-1">
                      <Input
                        label="Edit title and hit enter"
                        type="text"
                        placeholder="Project title"
                        :value="project.title"
                        @keydown.enter="
                          (e) => {
                            if (e.target.value) {
                              $resources.project.setValue.submit({
                                title: e.target.value,
                              })
                            }
                            $refs.editTitlePopup.close()
                          }
                        "
                      />
                      <Button @click="() => $refs.editTitlePopup.close()">
                        Cancel
                      </Button>
                    </div>
                  </div>
                </template>
              </Popover>
              <Dropdown
                placement="left"
                :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
                :options="[
                  {
                    label: 'Edit Title',
                    icon: 'edit',
                    handler: () => $refs.editTitlePopup.open(),
                  },
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
          </div>
        </div>
        <Tabs :tabs="tabs" class="border-none" />
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
            placeholder="Select a team"
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
    <div class="flex h-full min-h-0 flex-1 flex-col" v-if="project">
      <router-view class="h-full flex-1" :project="$resources.project" />
    </div>
  </div>
</template>
<script>
import { Autocomplete, Dropdown, Spinner, Input, Popover } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

export default {
  name: 'ProjectDetail',
  props: ['team', 'projectId'],
  components: {
    Input,
    Dropdown,
    Spinner,
    Pie,
    IconPicker,
    Links,
    Tabs,
    Breadcrumbs,
    Autocomplete,
    Popover,
  },
  data() {
    return {
      projectDeleteDialog: false,
      projectMoveDialog: { show: false, team: null },
    }
  },
  mounted() {
    let teams = this.$getListResource('Sidebar Teams')
    for (let team of teams.data || []) {
      if (team.name === this.team.doc.name) {
        team.open = true
        if (!team.projects.data) {
          team.projects.reload()
        }
      }
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
          route: {
            name: 'ProjectDetailOverview',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          isActive: this.$route.name === 'ProjectDetailOverview',
        },
        {
          name: `Discussions ${
            this.$resources.project.doc.discussions_count
              ? `(${this.$resources.project.doc.discussions_count})`
              : ''
          }`,
          route: {
            name: 'ProjectDetailDiscussions',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          isActive: [
            'ProjectDetailDiscussions',
            'ProjectDetailDiscussion',
          ].includes(this.$route.name),
        },
        {
          name: this.$resources.project.doc.summary.total_tasks
            ? `Tasks (${this.$resources.project.doc.summary.pending_tasks}/${this.$resources.project.doc.summary.total_tasks})`
            : 'Tasks',
          route: {
            name: 'ProjectTasks',
            query: { open: true },
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          isActive: [
            'ProjectTasks',
            'ProjectTaskDetail',
            'ProjectTaskNew',
          ].includes(this.$route.name),
        },
      ]
    },
  },
  methods: {
    onProjectMove() {
      this.projectMoveDialog.show = false
      this.$getListResource(['Team Projects', this.team.doc.name])?.reload()
      let teams = this.$getListResource('Sidebar Teams')
      for (let team of teams.data || []) {
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
  },
  pageMeta() {
    return {
      title: `${this.project.title} - ${this.team.doc.title}`,
      emoji: this.project.icon,
    }
  },
}
</script>
