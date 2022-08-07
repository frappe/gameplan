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
              <div class="text-lg font-medium leading-snug">
                {{ d.title }}
              </div>
              <div class="flex items-center justify-between mt-0.5 text-base">
                <div class="text-gray-600">
                  <span>by</span>
                  {{ user.full_name }}
                  <span>
                    {{
                      $dayjs().diff(d.modified, 'month') >= 9
                        ? 'on ' + $dayjs(d.modified).format('D MMM YYYY')
                        : $dayjs(d.modified).fromNow()
                    }}
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
                </div>
                <span
                  class="text-gray-600"
                  :title="discussionTimestampDescription(d)"
                >
                  {{
                    $dayjs().diff(d.modified, 'day') >= 25
                      ? $dayjs(d.modified).format('D MMM')
                      : $dayjs(d.modified).fromNow(true)
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
        class="flex items-center p-3 space-x-4"
        v-if="$resources.discussions.hasNextPage"
      >
        <div class="w-8 h-8 bg-gray-100 rounded-full"></div>
        <Button
          @click="$resources.discussions.next()"
          :loading="$resources.discussions.list.loading"
        >
          {{
            $resources.discussions.list.loading
              ? 'Loading...'
              : 'Load more posts'
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
  resources: {
    discussions() {
      return {
        type: 'list',
        cache: ['Team Project Discussion', this.filters],
        doctype: 'Team Project Discussion',
        filters: this.filters,
        fields: [
          'name',
          'owner',
          'creation',
          'modified',
          'last_post_at',
          'title',
          'status',
          'content',
          'team',
          'project',
          'project.title as project_title',
          'team.title as team_title',
        ],
        order_by: 'modified desc',
      }
    },
  },
  methods: {
    openLatestUpdate() {
      let latest = (this.$resources.discussions.data || [])[0]
      if (latest) {
        // open latest update
        this.$router.replace({
          name: 'ProjectStatusUpdatesView',
          params: { postId: latest.name },
        })
      }
    },
    isActive(update) {
      return this.$route.params.postId === update.name
    },
    discussionTimestampDescription(d) {
      return [
        `First Post: ${this.$dayjs(d.creation)}`,
        `Latest Post: ${this.$dayjs(d.modified)}`,
      ].join('\n')
    },
  },
}
</script>
