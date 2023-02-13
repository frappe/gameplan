<template>
  <div class="flex flex-col">
    <header class="sticky top-0 z-10 border-b bg-white px-5 pt-3">
      <div v-if="project">
        <div class="flex h-9 w-full items-center">
          <div class="rounded-md p-px text-5xl leading-none focus:outline-none">
            {{ team.doc.icon || '' }}
          </div>
          <router-link
            :to="{ name: 'Team', params: { teamId: team.doc.name } }"
            class="ml-1 rounded-md px-1 hover:bg-gray-200"
          >
            <h1 class="text-2xl font-medium text-gray-600">
              {{ team.doc.title }}
            </h1>
          </router-link>
          <FeatherIcon name="chevron-right" class="mx-0.5 w-5 text-gray-600" />
          <IconPicker
            ref="projectIconPicker"
            v-model="project.doc.icon"
            @update:modelValue="(icon) => project.setValue.submit({ icon })"
            :set-default="true"
          >
            <template v-slot="{ open }">
              <div
                class="rounded-md p-px text-5xl leading-none focus:outline-none"
                :class="open ? 'bg-gray-200' : 'hover:bg-gray-100'"
              >
                {{ project.doc.icon || '' }}
              </div>
            </template>
          </IconPicker>
          <div class="ml-2 flex items-center space-x-2">
            <h1 class="text-2xl font-medium leading-8">
              {{ project.doc.title }}
            </h1>
            <Badge v-if="project.doc.archived_at"> Archived </Badge>
            <Tooltip
              v-if="project.doc.is_private"
              text="This project is only visible to team members"
            >
              <Badge> Private </Badge>
            </Tooltip>
            <Dropdown
              v-if="$user().isNotGuest"
              placement="left"
              :button="{
                icon: 'more-horizontal',
                appearance: 'minimal',
                label: 'Options',
              }"
              :options="[
                {
                  label: 'Edit',
                  icon: 'edit',
                  handler: () => (projectEditDialog.show = true),
                  condition: () => !project.doc.archived_at,
                },
                {
                  label: 'Pin to home',
                  icon: PinIcon,
                  handler: () => pinProject(),
                  condition: () =>
                    !project.doc.is_pinned && !project.doc.archived_at,
                },
                {
                  label: 'Manage Guests',
                  icon: 'user-plus',
                  handler: () => (inviteGuestDialog.show = true),
                  condition: () => !project.doc.archived_at,
                },
                {
                  label: 'Move to another team',
                  icon: 'log-out',
                  handler: () => (projectMoveDialog.show = true),
                  condition: () => !project.doc.archived_at,
                },
                {
                  label: 'Archive this project',
                  icon: 'trash-2',
                  handler: archiveProject,
                  condition: () => !project.doc.archived_at,
                },
                {
                  label: 'Unarchive this project',
                  icon: 'trash-2',
                  handler: unarchiveProject,
                  condition: () => project.doc.archived_at,
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
                project.setValue.submit({
                  title: project.doc.title,
                  is_private: project.doc.is_private,
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
          <Input class="mb-2" label="Title" v-model="project.doc.title" />
          <Input
            label="Visibility"
            type="select"
            :options="[
              { label: 'Visible to everyone', value: 0 },
              { label: 'Visible to team members (Private)', value: 1 },
            ]"
            v-model="project.doc.is_private"
          />
          <ErrorMessage class="mt-2" :message="project.setValue.error" />
        </template>
      </Dialog>
      <Dialog
        :options="{
          title: 'Move project to another team',
        }"
        @close="
          () => {
            projectMoveDialog.team = null
            project.moveToTeam.reset()
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
          <ErrorMessage class="mt-2" :message="project.moveToTeam.error" />
        </template>
        <template #actions>
          <Button
            appearance="primary"
            :loading="project.moveToTeam.loading"
            @click="
              () => {
                project.moveToTeam.submit(
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
      <InviteGuestDialog
        v-if="$user().isNotGuest"
        v-model="inviteGuestDialog.show"
        :project="project"
      />
    </header>

    <router-view
      v-if="project"
      class="mx-auto w-full max-w-4xl px-5"
      :project="project"
    />
  </div>
</template>
<script>
import {
  Autocomplete,
  Dropdown,
  frappeRequest,
  Input,
  Tooltip,
} from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import InviteGuestDialog from '@/components/InviteGuestDialog.vue'
import { projects, getTeamProjects } from '@/data/projects'
import { teams } from '@/data/teams'
import PinIcon from '~icons/lucide/pin'

export default {
  name: 'Project',
  props: ['team', 'project'],
  components: {
    Input,
    Dropdown,
    Pie,
    IconPicker,
    Links,
    Tabs,
    Autocomplete,
    Tooltip,
    InviteGuestDialog,
  },
  setup() {
    return {
      PinIcon,
    }
  },
  data() {
    return {
      projectMoveDialog: { show: false, team: null },
      projectEditDialog: { show: false },
      inviteGuestDialog: { show: false },
    }
  },
  computed: {
    task() {
      let task = null
      if (this.$route.name === 'ProjectTaskDetail') {
        task = this.$getDocumentResource('GP Task', this.$route.params.taskId)
      }
      return task
    },
    tabs() {
      return [
        {
          name: 'Overview',
          route: {
            name: 'ProjectOverview',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.name,
            },
          },
          isActive: this.$route.name === 'ProjectOverview',
        },
        {
          name: `Discussions ${
            this.project.doc.discussions_count
              ? `(${this.project.doc.discussions_count})`
              : ''
          }`,
          route: {
            name: 'ProjectDiscussions',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.name,
            },
          },
          isActive: [
            'ProjectDiscussions',
            'ProjectDiscussion',
            'ProjectDiscussionNew',
          ].includes(this.$route.name),
        },
        {
          name: this.project.doc.summary.total_tasks
            ? `Tasks (${this.project.doc.summary.pending_tasks}/${this.project.doc.summary.total_tasks})`
            : 'Tasks',
          route: {
            name: 'ProjectTasks',
            query: { open: true },
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.name,
            },
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
    pinProject() {
      frappeRequest({
        url: 'frappe.client.insert',
        params: {
          doc: {
            doctype: 'GP Pinned Project',
            project: this.project.name,
          },
        },
      }).then(() => {
        this.project.reload()
        this.$toast({
          title: 'Project pinned to homescreen',
          icon: 'check-circle',
          iconClasses: 'text-green-600',
        })
      })
    },
    archiveProject() {
      this.$dialog({
        title: 'Archive Project',
        message: 'Are you sure you want to archive this project?',
        actions: [
          {
            label: 'Archive',
            appearance: 'primary',
            handler: ({ close }) => {
              return this.project.archive.submit(null, {
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
              return this.project.unarchive.submit(null, {
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
          projectId: this.project.name,
        },
      })
      this.projectMoveDialog.team = null
      this.project.moveToTeam.reset()
    },
    getTeamProjects,
  },
}
</script>
