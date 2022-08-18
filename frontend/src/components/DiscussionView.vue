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
            <Dropdown
              v-show="!editingContent"
              class="ml-auto"
              placement="right"
              :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
              :options="[
                {
                  label: 'Edit',
                  icon: 'edit',
                  handler: () => (editingContent = true),
                  condition: () => $user().name === discussion.owner,
                },
                {
                  label: 'Copy link',
                  icon: 'link',
                  handler: () => copyLink(),
                },
                {
                  label: 'Move to another project',
                  icon: 'log-out',
                  handler: () => (discussionMoveDialog.show = true),
                },
              ]"
            />
            <Button
              v-if="editingContent"
              @click="
                () => {
                  $resources.discussion.reload()
                  editingContent = false
                }
              "
            >
              Discard
            </Button>
            <Button
              v-if="editingContent"
              appearance="primary"
              @click="
                () => {
                  $resources.discussion.setValue.submit({
                    title: discussion.title,
                    content: discussion.content,
                  })
                  editingContent = false
                }
              "
            >
              Save
            </Button>
          </div>
        </div>
      </div>
      <div>
        <div v-if="editingContent" class="w-full mb-3">
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
        :key="editingContent"
        :editor-class="[
          'max-w-[unset] min-h-[8rem] prose-sm',
          { 'border px-3 py-2 rounded-b-lg': editingContent },
        ]"
        :editable="editingContent"
        :content="discussion.content"
        @change="discussion.content = $event"
        :bubbleMenu="editingContent"
        :fixedMenu="editingContent"
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

    <Dialog
      :options="{
        title: 'Move discussion to another project',
      }"
      @close="
        () => {
          discussionMoveDialog.project = null
          $resources.discussion.moveToProject.reset()
        }
      "
      v-model="discussionMoveDialog.show"
    >
      <template #body-content>
        <Autocomplete
          :options="
            $getListResource('Sidebar Teams')
              .data.find((d) => d.name == discussion.team)
              .projects.data.map((d) => ({
                label: d.title,
                value: d.name,
              }))
          "
          v-model="discussionMoveDialog.project"
          placeholder="Select a project"
        />
        <ErrorMessage
          class="mt-2"
          :message="$resources.discussion.moveToProject.error"
        />
      </template>
      <template #actions>
        <Button
          appearance="primary"
          :loading="$resources.discussion.moveToProject.loading"
          @click="
            () => {
              $resources.discussion.moveToProject.submit(
                { project: discussionMoveDialog.project?.value },
                {
                  validate() {
                    if (!discussionMoveDialog.project?.value) {
                      return 'Project is required to move this discussion'
                    }
                  },
                  onSuccess() {
                    onDiscussionMove()
                  },
                }
              )
            }
          "
        >
          {{
            discussionMoveDialog.project
              ? `Move to ${discussionMoveDialog.project.label}`
              : 'Move'
          }}
        </Button>
        <Button @click="discussionMoveDialog.show = false">Cancel</Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import { Autocomplete, Avatar, Dropdown, Dialog } from 'frappe-ui'
import Reactions from './Reactions.vue'
import CommentsArea from '@/pages/CommentsArea.vue'
import TextEditor from '@/components/TextEditor.vue'
import { copyToClipboard } from '@/utils'

export default {
  name: 'DiscussionView',
  props: ['postId'],
  components: {
    TextEditor,
    Avatar,
    Reactions,
    CommentsArea,
    Dropdown,
    Dialog,
    Autocomplete,
  },
  resources: {
    discussion() {
      return {
        type: 'document',
        doctype: 'Team Project Discussion',
        name: this.postId,
        whitelistedMethods: {
          trackVisit: 'track_visit',
          moveToProject: 'move_to_project',
        },
        onSuccess(doc) {
          if (!this.$route.query.comment && doc.last_unread_comment) {
            this.$router.replace({
              query: { comment: doc.last_unread_comment },
            })
          }
          if (this.visitTimer) {
            clearTimeout(this.visitTimer)
            this.visitTimer = null
          }
          this.visitTimer = setTimeout(() => {
            if (
              this.$route.name === 'ProjectDetailDiscussion' &&
              Number(this.$route.params.postId) === doc.name
            ) {
              this.$resources.discussion.trackVisit.submit()
            }
          }, 2000)
        },
      }
    },
  },
  data() {
    return {
      editingContent: false,
      discussionMoveDialog: {
        show: false,
        project: null,
      },
    }
  },
  methods: {
    getDoc(doctype, name) {
      return this.$getDocumentResource(doctype, name)?.doc
    },
    copyLink() {
      let location = window.location
      let url = `${location.origin}${location.pathname}`
      copyToClipboard(url)
    },
    onDiscussionMove() {
      this.discussionMoveDialog.show = false
      this.discussionMoveDialog.project = null

      this.$router.replace({
        name: 'ProjectDetailDiscussion',
        params: {
          teamId: this.discussion.team,
          projectId: this.discussion.project,
          postId: this.discussion.name,
        },
      })
      this.$resources.discussion.moveToProject.reset()
    },
  },
  computed: {
    discussion() {
      return this.$resources.discussion.doc
    },
  },
}
</script>
