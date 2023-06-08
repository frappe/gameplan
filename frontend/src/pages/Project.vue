<template>
  <div class="flex flex-col">
    <header class="sticky top-0 z-10 border-b bg-white px-5 pt-1">
      <div v-if="project">
        <div class="flex w-full items-center">
          <div class="rounded-md p-px text-xl leading-none focus:outline-none">
            {{ team.doc.icon || '' }}
          </div>
          <router-link
            :to="{ name: 'Team', params: { teamId: team.doc.name } }"
            class="ml-1 rounded-md px-1"
          >
            <h1 class="text-xl font-bold text-gray-600 hover:text-gray-900">
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
                class="rounded-md p-px text-xl leading-none focus:outline-none"
                :class="open ? 'bg-gray-200' : 'hover:bg-gray-100'"
              >
                {{ project.doc.icon || '' }}
              </div>
            </template>
          </IconPicker>
          <div class="ml-2 flex items-center space-x-2">
            <h1 class="text-xl font-bold text-gray-900">
              {{ project.doc.title }}
            </h1>
            <Badge v-if="project.doc.archived_at"> Archived </Badge>
            <Tooltip
              v-if="project.doc.is_private"
              text="This project is only visible to team members"
            >
              <FeatherIcon name="lock" class="h-4 w-4" />
            </Tooltip>
            <template v-if="!isMobile">
              <Button
                variant="ghost"
                v-if="project.doc.is_followed"
                @click="project.unfollow.submit()"
                :loading="project.unfollow.loading"
              >
                <template #prefix><LucideCheck class="w-4" /></template>
                Following
              </Button>
              <Button
                v-else
                variant="ghost"
                @click="project.follow.submit()"
                :loading="project.follow.loading"
              >
                <template #prefix><LucidePlus class="w-4" /></template>
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
        </div>
        <Tabs :tabs="tabs" class="border-none" />
      </div>
      <Dialog
        :options="{
          title: 'Edit Project',
          actions: [
            {
              label: 'Save',
              variant: 'solid',
              onClick() {
                return project.setValue.submit({
                  title: project.doc.title,
                  is_private: project.doc.is_private,
                })
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

    <router-view v-slot="{ Component, route }">
      <component
        v-if="project"
        :is="Component"
        :class="{ 'mx-auto w-full max-w-4xl px-5': !route.meta?.fullWidth }"
        :project="project"
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
import { projects, getTeamProjects } from '@/data/projects'
import { teams } from '@/data/teams'
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
          name: 'Tasks',
          route: {
            name: 'ProjectTasks',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.name,
              listType: 'active',
            },
          },
          isActive: [
            'ProjectTasks',
            'ProjectTaskDetail',
            'ProjectTaskNew',
          ].includes(this.$route.name),
        },
        {
          name: 'Pages',
          route: {
            name: 'ProjectPages',
            params: {
              teamId: this.team.doc.name,
              projectId: this.project.name,
            },
          },
          isActive: ['ProjectPages', 'ProjectPage', 'ProjectPageNew'].includes(
            this.$route.name
          ),
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
        title: 'Archive project',
        message: 'Are you sure you want to archive this project?',
        actions: [
          {
            label: 'Archive',
            variant: 'solid',
            onClick: ({ close }) => {
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
            onClick: ({ close }) => {
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
