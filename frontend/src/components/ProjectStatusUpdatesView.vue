<template>
  <div class="flex flex-col h-full" v-if="updateId && update">
    <div class="p-6">
      <div class="flex items-center space-x-4">
        <Avatar
          :label="$user(update.owner).full_name"
          :imageURL="$user(update.owner).user_image"
        />
        <div class="flex items-center w-full">
          <div>
            <span class="text-base text-gray-900">
              {{ $user(update.owner).full_name }} in
              <router-link
                class="hover:text-blue-600"
                :to="{
                  name: 'ProjectDetailOverview',
                  params: { teamId: update.team, projectId: update.project },
                }"
              >
                {{ update.team_title }} >
                {{ update.project_title }}
              </router-link>
            </span>
            &middot;
            <span class="text-base text-gray-600">
              {{ $dayjs(update.creation).fromNow() }}
            </span>
          </div>
          <Badge
            class="ml-auto"
            :color="{
              green: update.status === 'On Track',
              red: update.status === 'Off Track',
              yellow: update.status === 'At Risk',
            }"
          >
            {{ update.status }}
          </Badge>
        </div>
      </div>
      <TextEditor
        class="mt-3"
        editor-class="max-w-[unset] min-h-[8rem]"
        :content="content"
        :editable="false"
      />
      <Reactions
        doctype="Team Project Status Update"
        :name="update.name"
        v-model:reactions="update.reactions"
      />
    </div>
    <div class="flex-1 px-6 mt-6 border-t bg-gray-50">
      <CommentsArea doctype="Team Project Status Update" :name="update.name" />
    </div>
  </div>
  <div class="grid h-full text-base place-items-center bg-gray-50" v-else>
    <span class="px-3 py-1 text-gray-600 bg-white border rounded-full">
      Select an update to view
    </span>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Reactions from './Reactions.vue'
import CommentsArea from '../pages/CommentsArea.vue'

export default {
  name: 'ProjectStatusUpdatesView',
  props: ['updateId'],
  components: { TextEditor, Avatar, Reactions, CommentsArea },
  resources: {
    update() {
      return {
        type: 'list',
        doctype: 'Team Project Status Update',
        filters: { name: this.updateId },
        cache: ['Team Project Status Update', this.updateId],
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
        transform(data) {
          let updates = {}
          for (let d of data) {
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
          return Object.values(updates)[0]
        },
      }
    },
  },
  computed: {
    update() {
      return this.$resources.update.data
    },
    content() {
      return `<h2>${this.update.title}</h2>${this.update.content}`
    },
  },
}
</script>
