<template>
  <div class="flex flex-col">
    <router-view v-slot="{ Component, route }">
      <header
        class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
        v-if="!route.meta?.hideHeader"
      >
        <Breadcrumbs class="h-7" :items="breadcrumbs">
          <template #prefix="{ item }">
            <span class="mr-2 flex rounded-sm text-2xl leading-none" v-if="item.icon">
              {{ item.icon }}
            </span>
          </template>
        </Breadcrumbs>
        <div v-if="$route.name === 'ProjectOverview'" class="flex items-center space-x-2">
          <Tooltip
            v-if="project.doc.is_private"
            text="This project is only visible to team members"
          >
            <Badge size="lg">
              <template #prefix><span class="lucide-lock w-3" /></template>
              Private
            </Badge>
          </Tooltip>
          <Badge size="lg" v-if="project.doc.archived_at">
            <template #prefix><span class="lucide-archive w-3" /></template>
            Archived
          </Badge>
          <template v-if="!isMobile">
            <Button
              v-if="project.doc.is_followed"
              icon-left="lucide-bell"
              @click="project.unfollow.submit()"
              :loading="project.unfollow.loading"
            >
              Following
            </Button>
            <Button
              v-else
              icon-left="lucide-bell-plus"
              @click="project.follow.submit()"
              :loading="project.follow.loading"
            >
              Follow
            </Button>
          </template>
          <Dropdown
            v-if="$user().isNotGuest"
            align="start"
            :button="{
              icon: 'more-horizontal',
              variant: 'ghost',
              label: 'Options',
            }"
            :options="[
              {
                label: 'Edit',
                icon: 'lucide-edit',
                onClick: () => (projectEditDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Follow',
                icon: 'lucide-plus',
                onClick: () => project.follow.submit(),
                condition: () => isMobile && !project.doc.is_followed,
              },
              {
                label: 'Following',
                icon: 'lucide-check',
                onClick: () => project.unfollow.submit(),
                condition: () => isMobile && project.doc.is_followed,
              },
              {
                label: 'Manage Guests',
                icon: 'lucide-user-plus',
                onClick: () => (inviteGuestDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Move to another team',
                icon: 'lucide-log-out',
                onClick: () => (projectMoveDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Merge with another project',
                icon: 'lucide-merge',
                onClick: () => (projectMergeDialog.show = true),
              },
              {
                label: 'Archive this project',
                icon: 'lucide-trash-2',
                onClick: archiveProject,
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Unarchive this project',
                icon: 'lucide-trash-2',
                onClick: unarchiveProject,
                condition: () => project.doc.archived_at,
              },
            ]"
          />
        </div>
        <Dialog
          title="Edit Project"
          :actions="[
            {
              label: 'Save',
              variant: 'solid',
              onClick({ close }) {
                return project.setValue
                  .submit({
                    title: project.doc.title,
                    is_private: project.doc.is_private,
                  })
                  .then(close)
              },
            },
          ]"
          v-model:open="projectEditDialog.show"
        >
          <FormControl
            class="mb-2"
            label="Title"
            v-model="project.doc.title"
            placeholder="Project title"
          />
          <Select
            v-if="!team.doc.is_private"
            label="Visibility"
            :options="[
              { label: 'Visible to everyone', value: 0 },
              { label: 'Visible to team members (Private)', value: 1 },
            ]"
            v-model="project.doc.is_private"
          />
          <ErrorMessage class="mt-2" :message="project.setValue.error" />
        </Dialog>
        <Dialog
          title="Move project to another team"
          @close="
            () => {
              projectMoveDialog.team = null
              project.moveToTeam.reset()
            }
          "
          v-model:open="projectMoveDialog.show"
        >
          <Autocomplete
            :options="moveToTeamsList"
            v-model="projectMoveDialog.team"
            placeholder="Select a team"
          >
            <template #item-prefix="{ option }">
              <span class="mr-2">{{ option.icon }}</span>
            </template>
          </Autocomplete>
          <ErrorMessage class="mt-2" :message="project.moveToTeam.error" />
          <template #actions>
            <Button
              class="w-full"
              variant="solid"
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
                    },
                  )
                }
              "
            >
              {{ projectMoveDialog.team ? `Move to ${projectMoveDialog.team.label}` : 'Move' }}
            </Button>
          </template>
        </Dialog>
        <Dialog
          title="Merge with another project"
          @close="
            () => {
              projectMergeDialog.project = null
              project.mergeWithProject.reset()
            }
          "
          v-model:open="projectMergeDialog.show"
        >
          <p class="text-p-base text-ink-gray-7 mb-4">
            This will move all discussions, tasks, and pages from the
            <span class="whitespace-nowrap font-semibold">{{ project.doc.title }}</span> project to
            the selected project. This change is irreversible!
          </p>
          {{ projectMergeDialog.project }}
          <Autocomplete
            :options="mergeProjectsList"
            v-model="projectMergeDialog.project"
            placeholder="Select a project"
          >
            <template #item-prefix="{ option }">
              <span class="mr-2">{{ option.icon }}</span>
            </template>
          </Autocomplete>
          <ErrorMessage class="mt-2" :message="project.mergeWithProject.error" />
          <template #actions>
            <Button
              class="w-full"
              variant="solid"
              :loading="project.mergeWithProject.loading"
              @click="
                () => {
                  project.mergeWithProject.submit(
                    { project: projectMergeDialog.project?.value },
                    {
                      validate() {
                        if (!projectMergeDialog.project?.value) {
                          return 'Please select a project to merge'
                        }
                      },
                      onSuccess() {
                        if (projectMergeDialog.project.value) {
                          projectMergeDialog.show = false
                          return $router.replace({
                            name: 'Project',
                            params: { projectId: projectMergeDialog.project.value },
                          })
                        }
                      },
                    },
                  )
                }
              "
            >
              {{
                projectMergeDialog.project
                  ? `Merge with ${projectMergeDialog.project.label}`
                  : 'Merge'
              }}
            </Button>
          </template>
        </Dialog>
        <InviteGuestDialog
          v-if="$user().isNotGuest"
          v-model="inviteGuestDialog.show"
          :project="project"
        />
      </header>

      <component
        v-if="project"
        :is="Component"
        :class="{ 'mx-auto w-full max-w-4xl px-5': !route.meta?.fullWidth }"
        :project="project"
        :team="team"
      />
    </router-view>
  </div>
</template>
<script>
import {
  Autocomplete,
  Dropdown,
  FormControl,
  Breadcrumbs,
  frappeRequest,
  Input,
  Tooltip,
  Select,
  Textarea,
  dialog,
} from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import InviteGuestDialog from '@/components/InviteGuestDialog.vue'
import { projects } from '@/data/projects'
import { activeTeams, teams } from '@/data/teams'
import { isMobile as useMobile } from '@/composables/isMobile'

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
    FormControl,
    Select,
    Textarea,
    Breadcrumbs,
  },
  setup() {
    const isMobile = useMobile()
    return {
      isMobile,
    }
  },
  data() {
    return {
      projectMoveDialog: { show: false, team: null },
      projectEditDialog: { show: false },
      inviteGuestDialog: { show: false },
      projectMergeDialog: { show: false, project: null },
    }
  },
  computed: {
    moveToTeamsList() {
      return activeTeams.value
        .filter((d) => d.name != this.team.name)
        .map((d) => ({
          label: d.title,
          value: d.name,
          icon: d.icon,
        }))
    },
    mergeProjectsList() {
      return projects.data
        .filter((d) => d.name != this.project.name)
        .map((d) => ({
          label: d.title,
          value: d.name.toString(),
          icon: d.icon,
        }))
    },
    task() {
      let task = null
      if (this.$route.name === 'ProjectTaskDetail') {
        task = this.$getDocumentResource('GP Task', this.$route.params.taskId)
      }
      return task
    },
    breadcrumbs() {
      let items = [
        {
          label: this.team.doc.title,
          icon: this.team.doc.icon,
          route: { name: 'Team', params: { teamId: this.team.doc.name } },
        },
        {
          label: this.project.doc.title,
          route: {
            name: 'Project',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
            },
          },
        },
      ]
      if (
        ['ProjectDiscussions', 'ProjectDiscussion', 'ProjectDiscussionNew'].includes(
          this.$route.name,
        )
      ) {
        items.push({
          label: 'Discussions',
          route: {
            name: 'ProjectDiscussions',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
            },
          },
        })
      }
      if (this.$route.name === 'ProjectDiscussion') {
        let discussion = this.$getDocumentResource('GP Discussion', this.$route.params.postId)
        items.push({
          label: discussion?.doc?.title || this.$route.params.postId,
          route: {
            name: 'ProjectDiscussion',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
              postId: this.$route.params.postId,
            },
          },
        })
      }
      if (this.$route.name === 'ProjectDiscussionNew') {
        items.push({
          label: 'New Discussion',
          route: {
            name: 'ProjectDiscussionNew',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
            },
          },
        })
      }

      if (['ProjectTasks', 'ProjectTaskDetail'].includes(this.$route.name)) {
        items.push({
          label: 'Tasks',
          route: {
            name: 'ProjectTasks',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
            },
          },
        })
      }

      if (this.$route.name === 'ProjectTaskDetail') {
        let task = this.$getDocumentResource('GP Task', this.$route.params.taskId)
        items.push({
          label: task?.doc?.title || this.$route.params.taskId,
          route: {
            name: 'ProjectTaskDetail',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
              taskId: this.$route.params.taskId,
            },
          },
        })
      }

      if (['ProjectPages', 'ProjectPage'].includes(this.$route.name)) {
        items.push({
          label: 'Pages',
          route: {
            name: 'ProjectPages',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
            },
          },
        })
      }

      if (this.$route.name === 'ProjectPage') {
        let page = this.$getDocumentResource('GP Page', this.$route.params.pageId)
        items.push({
          label: page?.doc?.title || this.$route.params.pageId,
          route: {
            name: 'ProjectPage',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.doc.name,
              pageId: this.$route.params.pageId,
            },
          },
        })
      }

      return items
    },
  },
  methods: {
    archiveProject() {
      dialog.confirm({
        title: 'Archive project',
        message: 'Are you sure you want to archive this project?',
        confirmLabel: 'Archive',
        onConfirm: () => this.project.archive.submit(),
      })
    },
    unarchiveProject() {
      dialog.confirm({
        title: 'Unarchive Project',
        message: 'Are you sure you want to unarchive this project?',
        confirmLabel: 'Unarchive',
        onConfirm: () => this.project.unarchive.submit(),
      })
    },
    onProjectMove() {
      this.projectMoveDialog.show = false
      projects.reload()
      for (let team of teams.data || []) {
        if ([this.team.doc.name, this.projectMoveDialog.team.value].includes(team.name)) {
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
  },
}
</script>
