<template>
  <div class="flex flex-col h-full" v-if="postId && update">
    <div class="py-6">
      <div>
        <h1 class="text-3xl font-bold">{{ update.title }}</h1>
      </div>
      <div class="flex items-center space-x-2">
        <Avatar
          size="sm"
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
            <span
              class="text-base text-gray-600"
              :title="$dayjs(update.creation)"
            >
              {{ $dayjs(update.creation).fromNow() }}
            </span>
          </div>
          <div class="flex ml-auto space-x-2">
            <Button
              v-if="!editContent"
              icon="edit"
              @click="editContent = true"
            />
            <Button
              v-if="editContent"
              @click="
                () => {
                  $resources.update.reload()
                  editContent = false
                }
              "
            >
              Discard
            </Button>
            <Button
              v-if="editContent"
              appearance="primary"
              @click="
                () => {
                  $resources.update.setValue.submit({
                    name: update.name,
                    content: update.content,
                  })
                  editContent = false
                }
              "
            >
              Save
            </Button>
          </div>
        </div>
      </div>
      <TextEditor
        class="mt-3"
        :editor-class="[
          'max-w-[unset] min-h-[8rem]',
          { 'bg-gray-100 px-3 py-2 rounded-md': editContent },
        ]"
        :editable="editContent"
        :content="update.content"
        @change="update.content = $event"
      />
      <div class="mt-3">
        <Reactions
          doctype="Team Project Discussion"
          :name="update.name"
          v-model:reactions="update.reactions"
        />
      </div>
    </div>
    <div class="flex-1 border-t">
      <CommentsArea doctype="Team Project Discussion" :name="update.name" />
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
  name: 'DiscussionView',
  props: ['postId'],
  components: { TextEditor, Avatar, Reactions, CommentsArea },
  resources: {
    update() {
      return {
        type: 'list',
        doctype: 'Team Project Discussion',
        filters: { name: this.postId },
        cache: ['Team Project Discussion', this.postId],
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
  data() {
    return {
      editContent: false,
    }
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
