<template>
  <div class="h-full">
    <router-link
      v-for="d in $resources.discussions.data"
      :key="d.name"
      :to="{
        name: this.routeName,
        params: {
          teamId: d.team,
          projectId: d.project,
          postId: d.name,
          slug: d.slug,
        },
      }"
      class="group relative block rounded-[10px] hover:bg-gray-100"
    >
      <div class="flex items-center space-x-4 p-3">
        <UserInfo :email="d.last_post_by || d.owner">
          <template v-slot="{ user }">
            <div class="flex items-center space-x-3">
              <div
                class="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500"
                :class="d.unread ? 'visible' : 'invisible'"
              ></div>
              <component
                :is="d.closed_at ? 'Tooltip' : 'div'"
                class="flex"
                v-bind="
                  d.closed_at ? { text: 'This discussion is closed' } : null
                "
              >
                <div class="relative">
                  <UserAvatar :user="d.closed_by || user.name" />

                  <div
                    v-if="d.closed_at"
                    class="absolute bottom-0 right-0 rounded-full bg-green-100 p-0.5 ring-2 ring-white group-hover:ring-gray-100"
                  >
                    <FeatherIcon name="lock" class="h-3 w-3 text-green-500" />
                  </div>
                </div>
              </component>
            </div>
            <div class="w-full">
              <div class="flex items-center">
                <div :class="d.unread ? 'text-gray-900' : 'text-gray-600'">
                  <span
                    class="text-lg leading-snug"
                    :class="[d.unread ? 'font-semibold' : 'font-medium']"
                  >
                    {{ d.title }}
                  </span>
                  <span class="hidden whitespace-pre text-gray-600 md:inline">
                    &middot;
                  </span>
                  <span
                    class="hidden shrink-0 whitespace-nowrap text-sm text-gray-600 md:inline"
                    :title="discussionTimestampDescription(d)"
                  >
                    {{ discussionTimestamp(d) }}
                  </span>
                </div>
              </div>
              <div class="mt-0.5 flex items-center justify-between text-base">
                <div class="text-gray-600">
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
                <span
                  class="shrink-0 whitespace-nowrap text-sm text-gray-600 md:hidden"
                  :title="discussionTimestampDescription(d)"
                >
                  {{ discussionTimestamp(d) }}
                </span>
              </div>
            </div>
            <span
              class="ml-auto inline-flex shrink-0 items-center text-base"
              :class="d.unread ? 'text-gray-900' : 'text-gray-600'"
              v-if="d.comments_count"
            >
              {{ d.comments_count }}
              <FeatherIcon name="message-circle" class="ml-1 h-4 w-4" />
            </span>
          </template>
        </UserInfo>
      </div>
      <div class="ml-7 mr-3 h-px border-t border-gray-200"></div>
    </router-link>
    <div class="pb-40">
      <div
        v-if="
          !$resources.discussions.list.loading &&
          $resources.discussions.data.length === 0
        "
        class="flex flex-col items-center rounded-lg border-2 border-dashed py-8 text-base text-gray-600"
      >
        <FeatherIcon name="coffee" class="h-7 w-7 text-gray-500" />
        No discussions
      </div>
      <div
        class="flex items-center justify-center p-3"
        v-if="$resources.discussions.hasNextPage"
      >
        <Button
          @click="$resources.discussions.next"
          :loading="$resources.discussions.list.loading"
          icon-left="file-text"
        >
          {{
            $resources.discussions.loading ? 'Loading...' : 'Load more posts'
          }}
        </Button>
      </div>
    </div>
  </div>
</template>
<script>
import { TextEditor, Tooltip } from 'frappe-ui'
import FeatherIconCircle from './FeatherIconCircle.vue'

export default {
  name: 'DiscussionList',
  props: ['filters', 'routeName'],
  components: {
    TextEditor,
    FeatherIconCircle,
    Tooltip,
  },
  resources: {
    discussions() {
      return {
        type: 'list',
        doctype: 'Team Discussion',
        cache: ['Team Discussion', this.filters],
        url: 'gameplan.gameplan.doctype.team_discussion.api.get_discussions',
        filters: this.filters,
        auto: true,
        limit: 50,
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
      return this.$dayjs().diff(timestamp, 'day') >= 25
        ? this.$dayjs(timestamp).format('D MMM')
        : this.$dayjs(timestamp).fromNow()
    },
    discussionTimestampDescription(d) {
      return [
        `First Post: ${this.$dayjs(d.creation)}`,
        `Latest Post: ${this.$dayjs(d.last_post_at)}`,
      ].join('\n')
    },
  },
}
</script>
