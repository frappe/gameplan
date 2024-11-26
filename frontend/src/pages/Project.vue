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
              <template #prefix><LucideLock class="w-3" /></template>
              Private
            </Badge>
          </Tooltip>
          <Badge size="lg" v-if="project.doc.archived_at">
            <template #prefix><LucideArchive class="w-3" /></template>
            Archived
          </Badge>
          <template v-if="!isMobile">
            <Button
              v-if="project.doc.is_followed"
              @click="project.unfollow.submit()"
              :loading="project.unfollow.loading"
            >
              <template #prefix><LucideBell class="w-4" /></template>
              Following
            </Button>
            <Button v-else @click="project.follow.submit()" :loading="project.follow.loading">
              <template #prefix><LucideBellPlus class="w-4" /></template>
              Follow
            </Button>
          </template>
          <Dropdown
            v-if="$user().isNotGuest"
            placement="left"
            :button="{
              icon: 'more-horizontal',
              variant: 'ghost',
              label: 'Options',
            }"
            :options="[
              {
                label: 'Edit',
                icon: 'edit',
                onClick: () => (projectEditDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Follow',
                icon: 'plus',
                onClick: () => project.follow.submit(),
                condition: () => isMobile && !project.doc.is_followed,
              },
              {
                label: 'Following',
                icon: 'check',
                onClick: () => project.unfollow.submit(),
                condition: () => isMobile && project.doc.is_followed,
              },
              {
                label: 'Manage Guests',
                icon: 'user-plus',
                onClick: () => (inviteGuestDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Move to another team',
                icon: 'log-out',
                onClick: () => (projectMoveDialog.show = true),
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Archive this project',
                icon: 'trash-2',
                onClick: archiveProject,
                condition: () => !project.doc.archived_at,
              },
              {
                label: 'Unarchive this project',
                icon: 'trash-2',
                onClick: unarchiveProject,
                condition: () => project.doc.archived_at,
              },
            ]"
          />
        </div>
        <Dialog
          :options="{
            title: 'Edit Project',
            actions: [
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
            ],
          }"
          v-model="projectEditDialog.show"
        >
          <template #body-content>
            <FormControl
              class="mb-2"
              label="Title"
              v-model="project.doc.title"
              placeholder="Project title"
            />
            <FormControl
              v-if="!team.doc.is_private"
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
              :options="moveToTeamsList"
              v-model="projectMoveDialog.team"
              placeholder="Select a team"
            >
              <template #item-prefix="{ option }">
                <span class="mr-2">{{ option.icon }}</span>
              </template>
            </Autocomplete>
            <ErrorMessage class="mt-2" :message="project.moveToTeam.error" />
          </template>
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
import { computed } from 'vue'
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
} from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import IconPicker from '@/components/IconPicker.vue'
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
import InviteGuestDialog from '@/components/InviteGuestDialog.vue'
import { projects } from '@/data/projects'
import { activeTeams, teams } from '@/data/teams'
import PinIcon from '~icons/lucide/pin'
import { useScreenSize } from '@/utils/composables'

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
    const size = useScreenSize()
    const isMobile = computed(() => size.width < 640)
    return {
      PinIcon,
      isMobile,
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
    moveToTeamsList() {
      return activeTeams.value
        .filter((d) => d.name != this.team.name)
        .map((d) => ({
          label: d.title,
          value: d.name,
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
      this.$dialog({
        title: 'Archive project',
        message: 'Are you sure you want to archive this project?',
        actions: [
          {
            label: 'Archive',
            variant: 'solid',
            onClick: (close) => {
              return this.project.archive.submit(null, {
                onSuccess: close,
              })
            },
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
            variant: 'solid',
            onClick: (close) => {
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
