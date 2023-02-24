<template>
  <header
    class="fixed top-0 z-10 h-14 w-full border-b bg-white py-3 px-4 sm:sticky sm:px-5"
  >
    <div class="flex items-center justify-between">
      <div class="ml-3 flex">
        <h1 class="mr-4 text-2xl font-semibold">Home</h1>

        <div class="flex space-x-0.5">
          <Button
            appearance="minimal"
            v-for="option in feedOptions"
            :key="option.value"
            :active="feedType === option.value"
            @click="$router.replace({ params: { feedType: option.value } })"
          >
            {{ option.label }}
          </Button>
        </div>
      </div>
      <button
        @click="showCommandPalette"
        class="hidden w-full max-w-[20rem] rounded-md focus:outline-none focus:ring focus:ring-gray-300 md:block"
      >
        <Input
          :placeholder="searchPlaceholder"
          icon-left="search"
          class="cursor-pointer"
          :disabled="true"
        />
      </button>
    </div>
  </header>
  <div
    class="fixed top-14 flex w-full justify-center py-2 text-gray-600"
    v-if="swipeLoading"
  >
    <LoadingIndicator class="h-4 w-4" />
  </div>
  <div class="mt-14 pt-1 sm:mt-0">
    <div
      class="mx-auto -mt-1 flex max-w-4xl items-center justify-between px-2 pt-2 pb-2 sm:px-0 sm:px-5"
      v-if="feedType === 'following'"
    >
      <div class="text-base text-gray-700">
        <div v-if="$resources.followedProjects.data?.length === 0">
          You are not following any projects yet. Follow projects to see their
          discussions here.
        </div>

        <div class="text-base text-gray-700" v-else>
          You are following
          <span class="font-semibold">
            {{ $resources.followedProjects.data?.length }}
          </span>

          {{
            $resources.followedProjects.data?.length === 1
              ? 'project.'
              : 'projects.'
          }}
        </div>
      </div>

      <Button
        class="shrink-0"
        icon-left="plus"
        @click="followProjectsDialog = true"
      >
        Follow Projects
      </Button>
    </div>
    <DiscussionList
      ref="discussionList"
      class="mx-auto max-w-4xl sm:px-5"
      routeName="ProjectDiscussion"
      :filters="filters"
    />
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
                    icon="check"
                    appearance="minimal"
                    label="Unfollow project"
                    @click="unfollowProject(project.value)"
                    :loading="
                      $resources.followedProjects.delete.loading &&
                      $resources.followedProjects.delete.params.name ==
                        project.followId
                    "
                  />
                  <Button
                    v-else
                    icon="plus"
                    label="Follow project"
                    appearance="minimal"
                    @click="followProject(project.value)"
                    :loading="
                      $resources.followedProjects.insert.loading &&
                      $resources.followedProjects.insert.params?.doc?.name ==
                        project.value
                    "
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import { activeTeams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'
import { Autocomplete, LoadingIndicator } from 'frappe-ui'
import { getPlatform } from '@/utils'
import { showCommandPalette } from '@/components/CommandPalette.vue'
import { useSwipe } from '@/utils/composables'
import { getScrollContainer } from '@/utils/scrollContainer'

let projectFollowId = {}

export default {
  name: 'Home',
  props: ['feedType'],
  components: { Breadcrumbs, DiscussionList, Autocomplete, LoadingIndicator },
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
    showCommandPalette,
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
    searchPlaceholder() {
      let platform = getPlatform()
      if (platform == 'mac') {
        return 'Jump to project or team (⌘+K)'
      }
      return 'Jump to project or team (Ctrl+K)'
    },
  },
  pageMeta() {
    return {
      title: 'Home',
    }
  },
}
</script>
