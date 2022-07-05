<template>
  <div class="h-full space-y-5">
    <template v-for="d in $resources.updates.data" :key="d.name">
      <router-link
        :to="{
          name: this.routeName,
          params: { postId: d.name },
          replace: true,
        }"
        class="block p-3 border rounded-xl"
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
                  <div class="text-base text-gray-900">
                    {{ user.full_name }}
                    <template v-if="!filters">
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
                  </div>
                  <div
                    class="text-base text-gray-600"
                    :title="$dayjs(d.creation)"
                  >
                    {{ $dayjs(d.creation).fromNow() }}
                  </div>
                </div>
              </div>
            </template>
          </UserInfo>
        </div>
        <div class="mt-3 text-xl font-semibold">
          {{ d.title }}
        </div>
        <div class="mt-3 overflow-hidden prose-sm prose max-h-12">
          {{ summary(d.content) }}
        </div>

        <Reactions
          class="mt-3"
          v-model:reactions="d.reactions"
          doctype="Team Project Discussion"
          :name="d.name"
        />
      </router-link>
    </template>
    <div class="h-10"></div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import { htmlToText } from 'html-to-text'

export default {
  name: 'DiscussionList',
  props: ['filters', 'routeName'],
  components: {
    TextEditor,
    Avatar,
    Link,
    Reactions,
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
          'reactions.name as reaction_name',
          'reactions.emoji as reaction_emoji',
          'reactions.owner as reaction_owner',
        ],
        order_by: 'creation desc',
        transform(data) {
          let order = []
          let updates = {}
          for (let d of data) {
            if (!order.includes(d.name)) {
              order.push(d.name)
            }
            if (!updates[d.name]) {
              updates[d.name] = d
              updates[d.name].reactions = []
            }
            if (d.reaction_emoji) {
              updates[d.name].reactions.push({
                name: d.reaction_name,
                emoji: d.reaction_emoji,
                owner: d.reaction_owner,
              })
            }
          }
          return order.map((d) => updates[d])
        },
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
    summary(content) {
      return htmlToText(content, {
        selectors: [
          { selector: 'h1', options: { uppercase: false } },
          { selector: 'h2', options: { uppercase: false } },
          { selector: 'h3', options: { uppercase: false } },
          { selector: 'h4', options: { uppercase: false } },
          { selector: 'h5', options: { uppercase: false } },
          { selector: 'h6', options: { uppercase: false } },
        ],
      })
    },
  },
}
</script>
