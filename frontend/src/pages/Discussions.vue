<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
  >
    <Breadcrumbs class="h-7" :items="[{ label: 'Discussions', route: { name: 'Discussions' } }]" />
    <Button variant="solid" :route="{ name: 'NewDiscussion' }">
      <template #prefix><LucidePlus class="h-4 w-4" /></template>
      Start a discussion
    </Button>
  </header>
  <div class="mx-auto max-w-4xl pt-6 sm:px-5">
    <div class="mb-4 flex items-center justify-between px-3">
      <TabButtons :buttons="feedOptions" v-model="feedType" />
      <Dropdown
        placement="right"
        :button="{ icon: LucideSettings2 }"
        :options="[{ group: 'Order by', items: orderOptions }]"
      />
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
</template>
<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { Breadcrumbs, Dropdown, TabButtons } from 'frappe-ui'
import { useSwipe } from '@/utils/composables'
import DiscussionList from '@/components/DiscussionList.vue'
import LucideSettings2 from '~icons/lucide/settings-2.vue'
import LucideCheck from '~icons/lucide/check.vue'

let orderBy = ref('last_post_at desc')
let feedType = ref('relevant')
const NoIcon = h('div')

let orderOptions = computed(() => [
  {
    label: 'Last post',
    value: 'last_post_at desc',
    icon: orderBy.value === 'last_post_at desc' ? LucideCheck : NoIcon,
    onClick: () => {
      orderBy.value = 'last_post_at desc'
    },
  },
  {
    label: 'Created',
    value: 'creation desc',
    icon: orderBy.value === 'creation desc' ? LucideCheck : NoIcon,
    onClick: () => {
      orderBy.value = 'creation desc'
    },
  },
])
let feedOptions = [
  {
    label: 'Relevant',
    value: 'relevant',
  },
  {
    label: 'All',
    value: 'all',
  },
]

let filters = computed(() => {
  return {
    ...(feedType.value && { feed_type: feedType.value }),
  }
})
</script>

<!-- <script>
import { computed, ref } from 'vue'
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
import StartDiscussionButton from '@/components/StartDiscussionButton.vue'

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
    StartDiscussionButton,
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
          label: 'Relevant',
          value: 'relevant',
        },
        {
          label: 'All',
          value: 'recent',
        },
      ],
      feedType: 'relevant',
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
</script> -->
