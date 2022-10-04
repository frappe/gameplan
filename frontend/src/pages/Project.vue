<template>
  <div class="flex h-full flex-col pt-8">
    <header>
      <div class="border-b" v-if="project">
        <div class="flex w-full items-start">
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
          <div class="ml-2 flex items-center space-x-2">
            <h1 class="text-6xl font-bold leading-8">
              {{ project.title }}
            </h1>
            <Badge v-if="$resources.project.doc.archived_at"> Archived </Badge>
            <Tooltip
              v-if="$resources.project.doc.is_private"
              text="This project is only visible to team members"
              placement="top"
            >
              <Badge> Private </Badge>
            </Tooltip>
            <Dropdown
              placement="left"
              :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
              :options="[
                {
                  label: 'Edit',
                  icon: 'edit',
                  handler: () => (projectEditDialog.show = true),
                  condition: () => !$resources.project.doc.archived_at,
                },
                {
                  label: 'Move to another team',
                  icon: 'log-out',
                  handler: () => (projectMoveDialog.show = true),
                  condition: () => !$resources.project.doc.archived_at,
                },
                {
                  label: 'Archive this project',
                  icon: 'trash-2',
                  handler: archiveProject,
                  condition: () => !$resources.project.doc.archived_at,
                },
                {
                  label: 'Unarchive this project',
                  icon: 'trash-2',
                  handler: unarchiveProject,
                  condition: () => $resources.project.doc.archived_at,
                },
              ]"
            />
          </div>
        </div>
        <Tabs :tabs="tabs" class="border-none" />
      </div>
      <Dialog
        :options="{
          title: 'Edit Project',
          actions: [
            {
              label: 'Save',
              appearance: 'primary',
              handler: ({ close }) => {
                $resources.project.setValue.submit({
                  title: project.title,
                  is_private: project.is_private,
                })
                close()
              },
            },
            {
              label: 'Cancel',
            },
          ],
        }"
        v-model="projectEditDialog.show"
      >
        <template #body-content>
          <Input
            class="mb-2"
            label="Title"
            v-model="$resources.project.doc.title"
          />
          <Input
            label="Visibility"
            type="select"
            :options="[
              { label: 'Visible to everyone', value: 0 },
              { label: 'Visible to team members (Private)', value: 1 },
            ]"
            v-model="$resources.project.doc.is_private"
          />
          <ErrorMessage
            class="mt-2"
            :message="$resources.project.setValue.error"
          />
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
              $getListResource('Teams')
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
import { Autocomplete, Dropdown, Spinner, Input, Tooltip } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { projects, getTeamProjects } from '@/data/projects'
import { teams } from '@/data/teams'

export default {
  name: 'Project',
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
    Tooltip,
  },
  data() {
    return {
      projectMoveDialog: { show: false, team: null },
      projectEditDialog: { show: false },
    }
  },
  mounted() {
    for (let team of teams.data || []) {
      if (team.name === this.team.doc.name) {
        team.open = true
      }
    }
  },
  resources: {
    project() {
      return {
        type: 'document',
        doctype: 'Team Project',
        name: this.projectId,
        realtime: true,
        whitelistedMethods: {
          moveToTeam: 'move_to_team',
          archive: 'archive',
          unarchive: 'unarchive',
          inviteMembers: 'invite_members',
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
            name: 'ProjectOverview',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          isActive: this.$route.name === 'ProjectOverview',
        },
        {
          name: `Discussions ${
            this.$resources.project.doc.discussions_count
              ? `(${this.$resources.project.doc.discussions_count})`
              : ''
          }`,
          route: {
            name: 'ProjectDiscussions',
            params: { teamId: this.team.doc.name, projectId: this.projectId },
          },
          isActive: [
            'ProjectDiscussions',
            'ProjectDiscussion',
            'ProjectDiscussionNew',
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
    archiveProject() {
      this.$dialog({
        title: 'Archive Project',
        message: 'Are you sure you want to archive this project?',
        actions: [
          {
            label: 'Archive',
            appearance: 'primary',
            handler: ({ close }) => {
              return this.$resources.project.archive.submit(null, {
                onSuccess: close,
              })
            },
          },
          {
            label: 'Cancel',
          },
        ],
      })
    },
    unarchiveProject() {
      this.$dialog({
        title: 'Unarchive Project',
        message: 'Are you sure you want to unarchive this project?',
        actions: [
          {
            label: 'Unarchive',
            appearance: 'primary',
            handler: ({ close }) => {
              return this.$resources.project.unarchive.submit(null, {
                onSuccess: close,
              })
            },
          },
          {
            label: 'Cancel',
          },
        ],
      })
    },
    onProjectMove() {
      this.projectMoveDialog.show = false
      projects.reload()
      for (let team of teams.data || []) {
        if (
          [this.team.doc.name, this.projectMoveDialog.team.value].includes(
            team.name
          )
        ) {
          if (this.projectMoveDialog.team.value === team.name) {
            team.open = true
          }
        }
      }
      this.$router.push({
        name: 'ProjectOverview',
        params: {
          teamId: this.projectMoveDialog.team.value,
          projectId: this.projectId,
        },
      })
      this.projectMoveDialog.team = null
      this.$resources.project.moveToTeam.reset()
    },
    getTeamProjects,
  },
  pageMeta() {
    return {
      title: `${this.project.title} - ${this.team.doc.title}`,
      emoji: this.project.icon,
    }
  },
}
</script>
