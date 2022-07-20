<template>
  <div class="h-full divide-y">
    <router-link
      v-for="d in $resources.updates.data"
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
            <div class="flex items-start w-full">
              <div>
                <div class="text-lg font-medium leading-snug">
                  {{ d.title }}
                </div>
                <div class="mt-1 text-base text-gray-900">
                  <span class="text-gray-600"> by </span>
                  {{ user.full_name }}
                  <template v-if="!filters || !filters.project">
                    <span class="text-gray-600">in&nbsp;</span>
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
                  <span class="text-gray-600" :title="$dayjs(d.creation)">
                    &middot;
                    {{ $dayjs(d.creation).fromNow() }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </UserInfo>
      </div>
    </router-link>
    <div class="p-3 pb-40 pl-14">
      <Button
        v-if="$resources.updates.hasNextPage"
        class="ml-1"
        @click="$resources.updates.next()"
        :loading="$resources.updates.list.loading"
      >
        Load more posts
      </Button>
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
    updates() {
      return {
        type: 'list',
        cache: ['Project Updates', this.filters],
        doctype: 'Team Project Discussion',
        filters: this.filters,
        fields: [
          'name',
          'owner',
          'creation',
          'modified',
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
      let latest = (this.$resources.updates.data || [])[0]
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
  },
}
</script>
