<template>
  <div class="h-full">
    <router-link
      v-for="(d, index) in $resources.discussions.data"
      :key="d.name"
      :to="{
        name: 'ProjectDiscussion',
        params: {
          teamId: d.team,
          projectId: d.project,
          postId: d.name,
          slug: d.slug,
        },
      }"
      class="group relative block h-15 rounded-[10px] transition hover:bg-gray-100"
    >
      <div class="flex h-full items-center space-x-4 overflow-hidden px-3 py-2">
        <UserInfo :email="d.last_post_by || d.owner">
          <template v-slot="{ user }">
            <div class="flex items-center space-x-3">
              <component
                :is="
                  d.closed_at || (d.pinned_at && this.filters)
                    ? 'Tooltip'
                    : 'div'
                "
                class="flex"
                v-bind="
                  d.closed_at
                    ? { text: 'This discussion is closed' }
                    : d.pinned_at
                    ? { text: 'This discussion is pinned' }
                    : null
                "
              >
                <div class="relative flex">
                  <UserAvatar :user="d.closed_by || user.name" size="2xl" />

                  <div
                    v-if="d.closed_at"
                    class="absolute bottom-0 right-0 rounded-full bg-gray-100 p-0.5 ring-2 ring-white group-hover:ring-gray-100"
                  >
                    <LucideLock class="h-3 w-3 text-gray-900" />
                  </div>
                  <div
                    v-if="d.pinned_at && this.filters"
                    class="absolute bottom-0 right-0 rounded-full bg-gray-100 p-0.5 ring-2 ring-white group-hover:ring-gray-100"
                  >
                    <LucidePin class="h-3 w-3 rotate-45 text-gray-900" />
                  </div>
                </div>
              </component>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex min-w-0 items-center">
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap leading-none"
                  :class="d.unread ? 'text-gray-900' : 'text-gray-900'"
                >
                  <span
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-base"
                    :class="[d.unread ? 'font-semibold' : 'font-medium']"
                  >
                    {{ d.title }}
                  </span>
                </div>
              </div>
              <div class="mt-1.5 flex min-w-0 items-center justify-between">
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-base text-gray-600"
                >
                  <span :class="filters ? '' : 'hidden sm:inline'">
                    {{ user.full_name }}
                  </span>
                  <template v-if="!filters || !filters.project">
                    <span> in </span>
                    <span>
                      {{ d.team_title }}
                      <span class="text-gray-500"> &mdash; </span>
                      {{ d.project_title }}
                    </span>
                  </template>
                </div>
              </div>
            </div>
            <div class="ml-auto">
              <div
                class="shrink-0 whitespace-nowrap text-sm text-gray-600"
                :title="discussionTimestampDescription(d)"
              >
                {{ discussionTimestamp(d) }}
              </div>
              <div class="mt-1.5 flex items-center justify-end space-x-3">
                <Tooltip text="Ongoing poll" v-if="d.ongoing_polls?.length">
                  <LucideBarChart2 class="h-4 w-4 -rotate-90" />
                </Tooltip>
                <Badge>{{ d.comments_count + 1 }}</Badge>
              </div>
            </div>
          </template>
        </UserInfo>
      </div>
      <div
        class="mx-3 h-px border-t border-gray-200"
        v-if="index < $resources.discussions.data.length - 1"
      ></div>
      <div
        class="absolute left-1 top-[30px] h-3.5 w-3.5 shrink-0 -translate-y-1/2 rounded-full border-[3px] border-white bg-orange-500 sm:-left-2.5 sm:h-1.5 sm:w-1.5 sm:border-none"
        :class="d.unread ? 'visible' : 'invisible'"
      ></div>
    </router-link>
    <div class="px-2 sm:px-0">
      <div
        v-if="
          !$resources.discussions.list.loading &&
          $resources.discussions.data.length === 0
        "
        class="flex flex-col items-center rounded-lg border-2 border-dashed py-8 text-base text-gray-600"
      >
        <LucideCoffee class="h-7 w-7 text-gray-500" />
        No discussions
      </div>
      <div
        class="flex items-center justify-center p-3"
        v-if="!hideLoadMore && $resources.discussions.hasNextPage"
      >
        <Button
          @click="$resources.discussions.next"
          :loading="$resources.discussions.list.loading"
        >
          <template #prefix>
            <LucideRefreshCw class="h-4 w-4" />
          </template>
          {{ $resources.discussions.loading ? 'Loading...' : 'Load more' }}
        </Button>
      </div>
    </div>
  </div>
</template>
<script>
import { TextEditor, Tooltip } from 'frappe-ui'

export default {
  name: 'DiscussionList',
  props: {
    listOptions: {
      type: Object,
      default: () => ({}),
    },
    hideLoadMore: {
      type: Boolean,
      default: false,
    },
  },
  expose: ['discussions'],
  components: {
    TextEditor,
    Tooltip,
  },
  resources: {
    discussions() {
      return {
        type: 'list',
        doctype: 'GP Discussion',
        cache: ['Discussions', this.listOptions],
        url: 'gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
        filters: this.listOptions.filters,
        auto: true,
        pageLength: this.listOptions.pageLength || 50,
        orderBy: this.listOptions.orderBy || 'last_post_at desc',
        transform(data) {
          for (let d of data) {
            d.unread = !d.last_visit || d.last_post_at > d.last_visit
          }
          return data
        },
      }
    },
  },
  methods: {
    isActive(update) {
      return Number(this.$route.params.postId) === update.name
    },
    discussionTimestamp(d) {
      let timestamp = d.last_post_at || d.creation
      if (this.$dayjs().diff(timestamp, 'day') < 25) {
        return this.$dayjs(timestamp).fromNow()
      }
      if (this.$dayjs().diff(timestamp, 'year') < 1) {
        return this.$dayjs(timestamp).format('D MMM')
      }
      return this.$dayjs(timestamp).format('D MMM YYYY')
    },
    discussionTimestampDescription(d) {
      return [
        `First Post: ${this.$dayjs(d.creation)}`,
        `Latest Post: ${this.$dayjs(d.last_post_at)}`,
      ].join('\n')
    },
  },
  computed: {
    discussions() {
      return this.$resources.discussions
    },
    filters() {
      return this.listOptions.filters
    },
  },
  activated() {
    this.$resources.discussions.reload()
  },
}
</script>
