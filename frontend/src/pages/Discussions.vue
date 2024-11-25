<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
  >
    <Breadcrumbs class="h-7" :items="[{ label: 'Discussions', route: { name: 'Discussions' } }]" />
    <Button variant="solid" @click="newDiscussionDialog.show = true">
      <template #prefix><LucidePlus class="h-4 w-4" /></template>
      Add new
    </Button>
  </header>
  <div
    class="fixed inset-x-0 top-14 flex w-full justify-center py-2 text-ink-gray-5"
    v-if="swipeLoading"
  >
    <LoadingIndicator class="h-4 w-4" />
  </div>
  <div class="mx-auto max-w-4xl pt-4 sm:px-5">
    <div class="mb-5 flex items-center justify-between px-3 sm:px-0">
      <TabButtons :buttons="feedOptions" v-model="feedType" />
      <Button
        v-if="feedType === 'following'"
        class="shrink-0"
        @click="followProjectsDialog = true"
        variant="subtle"
      >
        <template #prefix><LucideBellPlus class="w-4" /></template>
        {{ $resources.followedProjects.data.length }}
        {{ $resources.followedProjects.data.length === 1 ? 'Project' : 'Projects' }}
      </Button>
      <Select class="pr-7" v-if="feedType === 'recent'" :options="orderOptions" v-model="orderBy" />
    </div>
    <KeepAlive>
      <DiscussionList
        ref="discussionList"
        routeName="ProjectDiscussion"
        :listOptions="{ filters, orderBy }"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>
  <Dialog
    v-model="followProjectsDialog"
    :options="{ title: 'Select projects to follow' }"
    @close="$refs.discussionList.discussions.reload()"
  >
    <template #body-content>
      <div>
        <div class="mt-1 gap-2">
          <div
            v-for="team in projectOptions"
            :key="team.group"
            @click="projects = projects.filter((p) => p !== project)"
            class="mb-4"
          >
            <div class="text-lg font-semibold text-ink-gray-9">
              {{ team.group }}
            </div>
            <div class="mt-1 divide-y divide-gray-100">
              <div
                class="flex items-center justify-between py-0.5"
                v-for="project in team.items"
                :key="project.value"
              >
                <div class="text-base text-ink-gray-8">
                  {{ project.label }}
                </div>
                <Button
                  v-if="isFollowed(project.value)"
                  variant="ghost"
                  label="Unfollow project"
                  @click="unfollowProject(project.value)"
                  :loading="
                    $resources.followedProjects.delete.loading &&
                    $resources.followedProjects.delete.params.name == project.followId
                  "
                >
                  <template #icon><LucideCheck class="w-4" /></template>
                </Button>
                <Button
                  v-else
                  label="Follow project"
                  variant="ghost"
                  @click="followProject(project.value)"
                  :loading="
                    $resources.followedProjects.insert.loading &&
                    $resources.followedProjects.insert.params?.doc?.name == project.value
                  "
                >
                  <template #icon><LucidePlus class="w-4" /></template>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
  <Dialog
    :options="{
      title: 'New Discussion',
      actions: [
        {
          label: 'Add new discussion',
          variant: 'solid',
          disabled: !newDiscussionDialog.project,
          onClick() {
            newDiscussionDialog.show = false
            $router.push({
              name: 'ProjectDiscussionNew',
              params: {
                projectId: newDiscussionDialog.project.value,
                teamId: newDiscussionDialog.project.team,
              },
            })
          },
        },
      ],
    }"
    v-model="newDiscussionDialog.show"
  >
    <template #body-content>
      <p class="mb-4 text-base text-ink-gray-7">Select a project to start a new discussion</p>
      <Autocomplete
        :options="projectOptions"
        v-model="newDiscussionDialog.project"
        placeholder="Select a project"
      />
    </template>
  </Dialog>
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'
import { activeTeams } from '@/data/teams'
import { getTeamProjects, activeProjects } from '@/data/projects'
import {
  Autocomplete,
  FormControl,
  LoadingIndicator,
  Select,
  TabButtons,
  Tooltip,
  Breadcrumbs,
} from 'frappe-ui'
import { useSwipe } from '@/utils/composables'
import { getScrollContainer } from '@/utils/scrollContainer'

let projectFollowId = {}

export default {
  components: {
    DiscussionList,
    Autocomplete,
    LoadingIndicator,
    Select,
    TabButtons,
    FormControl,
    Tooltip,
    Breadcrumbs,
  },
  data() {
    return {
      followProjectsDialog: false,
      newDiscussionDialog: { show: false, project: null },
      projects: [],
      selectedProject: null,
      swipeLoading: false,
      feedOptions: [
        {
          label: 'Recent',
          value: 'recent',
        },
        {
          label: 'Unread',
          value: 'unread',
        },
        {
          label: 'Following',
          value: 'following',
        },
      ],
      feedType: 'recent',
      orderOptions: [
        {
          label: 'Sort by',
          value: '',
          disabled: true,
        },
        {
          label: 'Last post',
          value: 'last_post_at desc',
        },
        {
          label: 'Created',
          value: 'creation desc',
        },
      ],
      orderBy: 'last_post_at desc',
    }
  },
  setup() {
    const swipe = useSwipe()
    return { swipe }
  },
  watch: {
    selectedProject(value) {
      if (!value) return
      if (!this.projects.includes(value)) {
        this.projects.push(value)
      }
      this.selectedProject = null
    },
    swipe: {
      handler(d) {
        if (getScrollContainer().scrollTop === 0 && d.direction == 'down' && d.diffY < -200) {
          this.swipeLoading = true
          this.$refs.discussionList.discussions.reload().then(() => {
            this.swipeLoading = false
          })
        }
      },
      deep: true,
    },
  },
  resources: {
    followedProjects() {
      return {
        type: 'list',
        doctype: 'GP Followed Project',
        fields: ['name', 'project', 'project.title'],
        auto: true,
        pageLength: 1000,
        onSuccess(data) {
          projectFollowId = {}
          data.forEach((p) => {
            projectFollowId[p.project] = p.name
          })
        },
      }
    },
  },
  methods: {
    followProject(project) {
      this.$resources.followedProjects.insert.submit({
        project,
      })
    },
    unfollowProject(project) {
      let followId = projectFollowId[project]
      if (!followId) return
      this.$resources.followedProjects.delete.submit(followId)
    },
    isFollowed(project) {
      let followedProjects = (this.$resources.followedProjects.data || []).map((p) =>
        parseInt(p.project),
      )
      return followedProjects.includes(project)
    },
  },
  computed: {
    filters() {
      const filters = {
        ...(this.feedType && { feed_type: this.feedType }),
        ...(activeProjects.value.length && {
          project: activeProjects.value.map((discussion) => Number(discussion.name)),
        }),
      }
      return filters
    },
    projectOptions() {
      return activeTeams.value.map((team) => ({
        group: team.title,
        items: getTeamProjects(team.name).map((project) => ({
          label: project.title,
          value: project.name,
          team: team.name,
          followId: projectFollowId[project.name],
        })),
      }))
    },
  },
  pageMeta() {
    return {
      title: 'Discussions',
    }
  },
}
</script>
