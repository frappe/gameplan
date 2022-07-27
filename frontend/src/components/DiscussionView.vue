<template>
  <div class="flex flex-col h-full" v-if="postId && discussion">
    <div class="py-6">
      <div class="flex items-center mb-3 space-x-2">
        <Avatar
          :label="$user(discussion.owner).full_name"
          :imageURL="$user(discussion.owner).user_image"
        />
        <div class="flex items-center w-full">
          <div>
            <span class="text-base text-gray-900">
              {{ $user(discussion.owner).full_name }} in
              <router-link
                class="hover:text-blue-600"
                :to="{
                  name: 'TeamPageHome',
                  params: {
                    teamId: discussion.team,
                  },
                }"
              >
                {{ getDoc('Team', discussion.team)?.title || discussion.team }}
              </router-link>
              >
              <router-link
                class="hover:text-blue-600"
                :to="{
                  name: 'ProjectDetailOverview',
                  params: {
                    teamId: discussion.team,
                    projectId: discussion.project,
                  },
                }"
              >
                {{
                  getDoc('Team Project', discussion.project)?.title ||
                  discussion.project
                }}
              </router-link>
            </span>
            &middot;
            <span
              class="text-base text-gray-600"
              :title="$dayjs(discussion.creation)"
            >
              {{ $dayjs(discussion.creation).fromNow() }}
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
                  $resources.discussion.reload()
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
                  $resources.discussion.setValue.submit({
                    title: discussion.title,
                    content: discussion.content,
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
      <div>
        <div v-if="editContent" class="w-full mb-3">
          <input
            type="text"
            class="w-full px-2 py-1 mt-1 text-xl font-semibold bg-gray-100 border-0 rounded-lg focus:ring-0"
            ref="title"
            v-model="discussion.title"
          />
        </div>
        <h1 v-else class="text-3xl font-bold">{{ discussion.title }}</h1>
      </div>
      <TextEditor
        :key="editContent"
        :editor-class="[
          'max-w-[unset] min-h-[8rem]',
          { 'border px-3 py-2 rounded-b-lg': editContent },
        ]"
        :editable="editContent"
        :content="discussion.content"
        @change="discussion.content = $event"
        :bubbleMenu="editContent"
        :fixedMenu="editContent"
      />
      <div class="mt-3">
        <Reactions
          doctype="Team Project Discussion"
          :name="discussion.name"
          v-model:reactions="discussion.reactions"
        />
      </div>
    </div>
    <div class="flex-1 pb-40 border-t">
      <CommentsArea doctype="Team Project Discussion" :name="discussion.name" />
    </div>
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
    discussion() {
      return {
        type: 'document',
        doctype: 'Team Project Discussion',
        name: this.postId,
        onSuccess(doc) {
          if (this.viewTimer) {
            console.log('clearing timeout for', doc.name)
            clearTimeout(this.viewTimer)
            this.viewTimer = null
          }
          console.log('started reading', doc.name)
          this.viewTimer = setTimeout(() => {
            if (
              this.$route.name === 'ProjectDetailDiscussion' &&
              this.$route.params.postId === doc.name
            ) {
              console.log('track view for ', doc.name)
              this.$resources.view.insert.submit({ discussion: this.postId })
            } else {
              console.log('skipped view for ', doc.name)
            }
          }, 3000)
        },
      }
    },
    view() {
      return {
        type: 'list',
        doctype: 'Team Discussion View',
        filters: {
          discussion: this.postId,
          viewed_by: this.$user().name,
        },
        limit: 1,
        order_by: 'creation desc',
      }
    },
  },
  data() {
    return {
      editContent: false,
    }
  },
  methods: {
    getDoc(doctype, name) {
      return this.$getDocumentResource(doctype, name)?.doc
    },
  },
  computed: {
    discussion() {
      return this.$resources.discussion.doc
    },
  },
}
</script>
