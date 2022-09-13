<template>
  <div class="relative flex h-full flex-col" v-if="postId && discussion">
    <div
      class="sticky top-0 z-10 -mx-4 border-b bg-white sm:mx-0"
      v-show="showNavbar"
    >
      <transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-4"
        enter-to-class="opacity-100 translate-y-0"
      >
        <div class="flex items-center px-6 sm:px-2 py-4" v-show="showNavbar">
          <UserProfileLink :user="discussion.owner">
            <Avatar
              :label="$user(discussion.owner).full_name"
              :imageURL="$user(discussion.owner).user_image"
            />
          </UserProfileLink>
          <h1 class="ml-3 text-2xl font-bold">
            {{ discussion.title }}
          </h1>
        </div>
      </transition>
    </div>

    <div class="py-6">
      <div class="mb-3 flex items-center space-x-2">
        <UserProfileLink :user="discussion.owner">
          <Avatar
            :label="$user(discussion.owner).full_name"
            :imageURL="$user(discussion.owner).user_image"
          />
        </UserProfileLink>
        <div class="flex w-full items-center">
          <div>
            <span class="text-base text-gray-900">
              <UserProfileLink
                class="font-medium hover:text-blue-600"
                :user="discussion.owner"
              >
                {{ $user(discussion.owner).full_name }}
              </UserProfileLink>
              in
              <router-link
                class="hover:text-blue-600"
                :to="{
                  name: 'TeamPageHome',
                  params: {
                    teamId: discussion.team,
                  },
                }"
              >
                {{ $getDoc('Team', discussion.team)?.title || discussion.team }}
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
                  $getDoc('Team Project', discussion.project)?.title ||
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
          <div class="ml-auto flex space-x-2">
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
        <div v-if="editingContent" class="mb-3 w-full">
          <input
            type="text"
            class="mt-1 w-full rounded-lg border-0 bg-gray-100 px-2 py-1 text-xl font-semibold focus:ring-0"
            ref="title"
            v-model="discussion.title"
          />
        </div>
        <h1
          v-else
          v-visibility="handleTitleVisibility"
          class="text-3xl font-bold"
        >
          {{ discussion.title }}
        </h1>
      </div>
      <TextEditor
        :key="editingContent"
        :editor-class="[
          'min-h-[8rem] prose-sm text-[15px]',
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
          doctype="Team Discussion"
          :name="discussion.name"
          v-model:reactions="discussion.reactions"
        />
      </div>
    </div>
    <div class="flex-1 pb-40">
      <CommentsArea doctype="Team Discussion" :name="discussion.name" />
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
          :options="projectOptions"
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
            $resources.discussion.moveToProject.submit({
              project: discussionMoveDialog.project?.value,
            })
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
import {
  Autocomplete,
  Avatar,
  Dropdown,
  Dialog,
  visibilityDirective,
} from 'frappe-ui'
import Reactions from './Reactions.vue'
import CommentsArea from '@/pages/CommentsArea.vue'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from './UserProfileLink.vue'
import { copyToClipboard } from '@/utils'
import { teams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'

export default {
  name: 'DiscussionView',
  props: ['postId'],
  directives: {
    visibility: visibilityDirective,
  },
  components: {
    TextEditor,
    Avatar,
    Reactions,
    CommentsArea,
    Dropdown,
    Dialog,
    Autocomplete,
    UserProfileLink,
  },
  resources: {
    discussion() {
      return {
        type: 'document',
        doctype: 'Team Discussion',
        name: this.postId,
        realtime: true,
        whitelistedMethods: {
          trackVisit: 'track_visit',
          moveToProject: {
            method: 'move_to_project',
            validate() {
              if (!this.discussionMoveDialog.project?.value) {
                return 'Project is required to move this discussion'
              }
            },
            onError() {
              this.discussionMoveDialog.show = true
            },
            onSuccess() {
              this.onDiscussionMove()
            },
          },
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
      showNavbar: false,
    }
  },
  methods: {
    copyLink() {
      let location = window.location
      let url = `${location.origin}${location.pathname}`
      copyToClipboard(url)
    },
    onDiscussionMove() {
      this.$nextTick(() => {
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
      })
      this.$resources.discussion.moveToProject.reset()
    },
    handleTitleVisibility(visible) {
      this.showNavbar = !visible
    },
  },
  computed: {
    discussion() {
      return this.$resources.discussion.doc
    },
    projectOptions() {
      return teams.data.map((team) => ({
        group: team.title,
        items: getTeamProjects(team.name).map((project) => ({
          label: project.title,
          value: project.name,
        })),
      }))
    },
  },
  pageMeta() {
    if (!this.discussion) return
    let project = this.$getDoc('Team Project', this.discussion.project)
    if (!project) return
    return {
      title: [this.discussion.title, project.title].filter(Boolean).join(' - '),
      emoji: project.icon,
    }
  },
}
</script>
