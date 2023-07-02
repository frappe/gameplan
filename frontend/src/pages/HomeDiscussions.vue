<template>
  <div
    class="fixed inset-x-0 top-14 flex w-full justify-center py-2 text-gray-600"
    v-if="swipeLoading"
  >
    <LoadingIndicator class="h-4 w-4" />
  </div>
  <div class="mx-auto max-w-4xl pt-6 sm:px-5">
    <div class="mb-4.5 flex items-center justify-between">
      <h2 class="text-xl font-semibold">Discussions</h2>
      <div class="flex items-center space-x-2">
        <Button
          v-if="feedType === 'following'"
          class="shrink-0"
          @click="followProjectsDialog = true"
          variant="ghost"
        >
          <template #prefix><LucideBellPlus class="w-4" /></template>
          {{ $resources.followedProjects.data.length }}
          {{
            $resources.followedProjects.data.length === 1
              ? 'Project'
              : 'Projects'
          }}
        </Button>

        <Select :options="feedOptions" v-model="feedType" />
      </div>
    </div>
    <KeepAlive>
      <DiscussionList
        ref="discussionList"
        routeName="ProjectDiscussion"
        :listOptions="{ filters }"
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
            <div class="text-lg font-semibold text-gray-900">
              {{ team.group }}
            </div>
            <div class="mt-1 divide-y divide-gray-100">
              <div
                class="flex items-center justify-between py-0.5"
                v-for="project in team.items"
                :key="project.value"
              >
                <div class="text-base text-gray-800">
                  {{ project.label }}
                </div>
                <Button
                  v-if="isFollowed(project.value)"
                  variant="ghost"
                  label="Unfollow project"
                  @click="unfollowProject(project.value)"
                  :loading="
                    $resources.followedProjects.delete.loading &&
                    $resources.followedProjects.delete.params.name ==
                      project.followId
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
                    $resources.followedProjects.insert.params?.doc?.name ==
                      project.value
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
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'
import { activeTeams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { Autocomplete, LoadingIndicator, Select } from 'frappe-ui'
import { useSwipe } from '@/utils/composables'
import { getScrollContainer } from '@/utils/scrollContainer'

let projectFollowId = {}

export default {
  name: 'Home',
  components: {
    DiscussionList,
    Autocomplete,
    LoadingIndicator,
    Select,
  },
  data() {
    return {
      followProjectsDialog: false,
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
        if (
          getScrollContainer().scrollTop === 0 &&
          d.direction == 'down' &&
          d.diffY < -200
        ) {
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
      let followedProjects = (this.$resources.followedProjects.data || []).map(
        (p) => parseInt(p.project)
      )
      return followedProjects.includes(project)
    },
  },
  computed: {
    filters() {
      return this.feedType ? { feed_type: this.feedType } : null
    },
    projectOptions() {
      return activeTeams.value.map((team) => ({
        group: team.title,
        items: getTeamProjects(team.name).map((project) => ({
          label: project.title,
          value: project.name,
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
