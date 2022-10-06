<template>
  <div class="h-full divide-y">
    <router-link
      v-for="d in $resources.discussions.data"
      :key="d.name"
      :to="{
        name: this.routeName,
        params: { teamId: d.team, projectId: d.project, postId: d.name },
      }"
      class="relative block hover:bg-gray-100"
    >
      <div
        v-show="d.unread"
        class="absolute -left-2 top-1/2 h-1.5 w-1.5 shrink-0 -translate-y-1/2 rounded-full bg-blue-300"
      ></div>
      <div class="flex items-center space-x-4 p-3">
        <UserInfo :email="d.last_post_by || d.owner">
          <template v-slot="{ user }">
            <FeatherIconCircle name="lock" color="green" v-if="d.closed_at" />
            <UserAvatar :user="user.name" v-else />
            <div class="w-full">
              <div class="flex items-center">
                <div :class="d.unread ? 'text-gray-900' : 'text-gray-600'">
                  <span class="text-lg font-medium leading-snug">
                    {{ d.title }}
                  </span>
                  <span class="hidden whitespace-pre text-gray-600 md:inline">
                    &middot;
                  </span>
                  <span
                    class="hidden shrink-0 whitespace-nowrap text-sm text-gray-600 md:inline"
                    :title="discussionTimestampDescription(d)"
                    >{{
                      $dayjs().diff(d.last_post_at, 'day') >= 25
                        ? $dayjs(d.last_post_at).format('D MMM')
                        : $dayjs(d.last_post_at).fromNow()
                    }}
                  </span>
                </div>
                <span
                  class="ml-auto inline-flex shrink-0 items-center text-base"
                  :class="d.unread ? 'text-gray-900' : 'text-gray-600'"
                  v-if="d.comments_count"
                >
                  {{ d.comments_count }}
                  <FeatherIcon name="message-circle" class="ml-1 h-4 w-4" />
                </span>
              </div>
              <div class="mt-0.5 flex items-center justify-between text-base">
                <div class="text-gray-600">
                  <span :class="filters ? '' : 'hidden sm:inline'">
                    {{ user.full_name }}
                  </span>
                  <template v-if="!filters || !filters.project">
                    <span> in </span>
                    <router-link
                      class="hover:text-blue-600"
                      :to="{
                        name: 'ProjectOverview',
                        params: { teamId: d.team, projectId: d.project },
                      }"
                    >
                      {{ d.team_title }}
                      <span class="text-gray-500"> &mdash; </span>
                      {{ d.project_title }}
                    </router-link>
                  </template>
                </div>
                <span
                  class="shrink-0 whitespace-nowrap text-sm text-gray-600 md:hidden"
                  :title="discussionTimestampDescription(d)"
                  >{{
                    $dayjs().diff(d.last_post_at, 'day') >= 25
                      ? $dayjs(d.last_post_at).format('D MMM')
                      : $dayjs(d.last_post_at).fromNow()
                  }}
                </span>
              </div>
            </div>
          </template>
        </UserInfo>
      </div>
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
        class="flex items-center space-x-4 p-3"
        v-if="$resources.discussions.hasNextPage"
      >
        <div class="h-8 w-8 rounded-full bg-gray-100"></div>
        <Button
          @click="$resources.discussions.next"
          :loading="$resources.discussions.list.loading"
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
import { TextEditor } from 'frappe-ui'
import FeatherIconCircle from './FeatherIconCircle.vue'

export default {
  name: 'DiscussionList',
  props: ['filters', 'routeName'],
  components: {
    TextEditor,
    FeatherIconCircle,
  },
  resources: {
    discussions() {
      return {
        type: 'list',
        doctype: 'Team Discussion',
        cache: ['Team Discussion', this.filters],
        method: 'gameplan.gameplan.doctype.team_discussion.api.get_discussions',
        filters: this.filters,
        auto: true,
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
    discussionTimestampDescription(d) {
      return [
        `First Post: ${this.$dayjs(d.creation)}`,
        `Latest Post: ${this.$dayjs(d.last_post_at)}`,
      ].join('\n')
    },
  },
}
</script>
