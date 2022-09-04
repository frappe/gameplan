<template>
  <div class="h-full divide-y">
    <router-link
      v-for="d in $resources.discussions.data"
      :key="d.name"
      :to="{
        name: this.routeName,
        params: { teamId: d.team, projectId: d.project, postId: d.name },
      }"
      class="block p-3"
      :class="isActive(d) ? 'bg-gray-100' : 'hover:bg-gray-50'"
    >
      <div class="flex items-center space-x-4">
        <div>
          <UserInfo :email="d.owner">
            <template v-slot="{ user }">
              <Avatar :label="user.full_name" :imageURL="user.user_image" />
            </template>
          </UserInfo>
        </div>
        <UserInfo :email="d.owner">
          <template v-slot="{ user }">
            <div class="w-full">
              <div class="flex items-center">
                <span
                  class="text-lg font-medium leading-snug"
                  :class="d.unread ? 'text-gray-900' : 'text-gray-600'"
                >
                  {{ d.title }}
                </span>
                <span
                  class="inline-block w-1.5 h-1.5 ml-1 mb-0.5 bg-blue-300 rounded-full"
                  v-if="d.unread"
                ></span>
                <span
                  class="inline-flex items-center ml-auto text-base"
                  :class="d.unread ? 'text-gray-900' : 'text-gray-600'"
                  v-if="d.comments_count"
                >
                  {{ d.comments_count }}
                  <FeatherIcon name="message-circle" class="w-4 h-4 ml-1" />
                </span>
              </div>
              <div class="flex items-center justify-between mt-0.5 text-base">
                <div class="text-gray-600">
                  <span :class="filters ? '' : 'hidden sm:inline'">
                    by {{ user.full_name }}
                  </span>
                  <template v-if="!filters || !filters.project">
                    <span> in </span>
                    <router-link
                      class="hover:text-blue-600"
                      :to="{
                        name: 'ProjectDetailOverview',
                        params: { teamId: d.team, projectId: d.project },
                      }"
                    >
                      {{ d.team_title }} >
                      {{ d.project_title }}
                    </router-link>
                  </template>
                  <span
                    class="text-gray-600 shrink-0"
                    :title="discussionTimestampDescription(d)"
                    >&nbsp;{{
                      $dayjs().diff(d.last_post_at, 'day') >= 25
                        ? 'on ' + $dayjs(d.last_post_at).format('D MMM')
                        : $dayjs(d.last_post_at).fromNow()
                    }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </UserInfo>
      </div>
    </router-link>
    <div class="pb-40">
      <div class="flex items-center p-3 space-x-4" v-if="hasNextPage">
        <div class="w-8 h-8 bg-gray-100 rounded-full"></div>
        <Button @click="nextPage" :loading="$resources.discussions.loading">
          {{
            $resources.discussions.loading ? 'Loading...' : 'Load more posts'
          }}
        </Button>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'

export default {
  name: 'DiscussionList',
  props: ['filters', 'routeName'],
  components: {
    TextEditor,
    Avatar,
  },
  data() {
    return {
      start: 0,
      hasNextPage: true,
    }
  },
  resources: {
    discussions() {
      return {
        cache: ['Team Discussion', this.filters],
        method:
          'gameplan.gameplan.doctype.team_discussion.api.get_discussions',
        makeParams() {
          return {
            filters: this.filters,
            start: this.start,
          }
        },
        auto: true,
        transform(data) {
          if (data.length < 20) {
            this.hasNextPage = false
          }
          for (let d of data) {
            d.unread = !d.last_visit || d.last_post_at > d.last_visit
          }
          if (this.start > 0) {
            let currentData = this.$resources.discussions.data || []
            return [...currentData, ...data]
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
    nextPage() {
      this.start += 20
      this.$resources.discussions.fetch()
    },
  },
}
</script>
