<template>
  <div class="relative flex h-full flex-col" v-if="postId && discussion">
    <header class="sticky top-0 z-10 border-b bg-white sm:mx-0">
      <div class="flex min-h-[60px] items-center px-4 sm:h-[60px]">
        <Button
          icon-left="chevron-left"
          appearance="minimal"
          @click="onBackClick"
          :class="['-ml-2 sm:ml-0', showNavbar && 'hidden sm:inline-flex']"
        >
          Back
        </Button>
        <transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0 translate-y-4"
          enter-to-class="opacity-100 translate-y-0"
        >
          <div
            class="mx-auto w-full max-w-3xl sm:px-6 sm:text-center"
            v-show="showNavbar"
          >
            <h1
              class="flex items-center pt-2 text-xl font-semibold sm:justify-center sm:pt-0"
            >
              <Tooltip
                class="flex"
                v-if="discussion.closed_at"
                text="This discussion is closed"
              >
                <FeatherIcon
                  name="lock"
                  class="mr-2 h-4 w-4 text-gray-700"
                  :stroke-width="2"
                />
              </Tooltip>
              {{ discussion.title }}
            </h1>
            <DiscussionMeta :discussion="discussion" class="pb-2 sm:pb-0" />
          </div>
        </transition>
        <div class="ml-auto flex items-center space-x-2">
          <Dropdown
            v-if="!readOnlyMode"
            class="ml-auto"
            placement="right"
            :button="{
              icon: 'more-horizontal',
              appearance: 'minimal',
              label: 'Discussion Options',
            }"
            :options="actions"
          />
        </div>
      </div>
    </header>

    <div class="mx-auto w-full max-w-3xl px-6">
      <div class="py-6">
        <div>
          <div v-if="editingTitle" class="mb-3 w-full">
            <div class="mb-2">
              <input
                v-if="editingTitle"
                type="text"
                class="w-full rounded-lg border-0 bg-gray-100 px-2 py-1 text-xl font-semibold focus:ring-0"
                ref="title"
                v-model="discussion.title"
                placeholder="Title"
                @keydown.enter="
                  () => {
                    $resources.discussion.setValue
                      .submit({ title: discussion.title })
                      .then(() => this.updateUrlSlug())
                    editingTitle = false
                  }
                "
                @keydown.esc="
                  () => {
                    $resources.discussion.reload()
                    editingTitle = false
                  }
                "
                v-focus
              />
              <p class="mt-1 text-sm text-gray-600">
                Edit title and press enter. Press escape to cancel.
              </p>
            </div>
          </div>
          <h1
            v-else
            v-visibility="handleTitleVisibility"
            class="flex items-center text-3xl font-bold"
          >
            <Tooltip
              v-if="discussion.closed_at"
              text="This discussion is closed"
            >
              <FeatherIcon
                name="lock"
                class="mr-2 h-4 w-4 text-gray-700"
                :stroke-width="2"
              />
            </Tooltip>
            <span>
              {{ discussion.title }}
            </span>
          </h1>
        </div>
        <div class="flex items-center text-base" v-show="!editingTitle">
          <DiscussionBreadcrumbs :discussion="discussion" />
          <span class="px-1.5">&middot;</span>
          <span class="text-gray-600">
            {{
              discussion.participants_count == 1
                ? `1 participant`
                : `${discussion.participants_count} participants`
            }}
          </span>
        </div>
        <div class="mt-6 mb-2 flex w-full items-center">
          <UserProfileLink class="mr-3" :user="discussion.owner">
            <UserAvatar :user="discussion.owner" />
          </UserProfileLink>
          <div class="flex flex-col md:block">
            <UserProfileLink
              class="text-base font-medium hover:text-blue-600"
              :user="discussion.owner"
            >
              {{ $user(discussion.owner).full_name }}
              <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
            </UserProfileLink>
            <time
              class="text-base text-gray-600"
              :datetime="discussion.creation"
              :title="$dayjs(discussion.creation)"
            >
              {{ $dayjs(discussion.creation).fromNow() }}
            </time>
          </div>
          <div class="ml-auto flex space-x-2">
            <Button
              v-if="
                !readOnlyMode &&
                $user().name === discussion.owner &&
                !editingContent
              "
              appearance="minimal"
              icon="edit"
              @click="editingContent = true"
              label="Edit Post"
            >
              Edit
            </Button>
          </div>
        </div>
        <div
          :class="{
            'rounded-lg border p-4 focus-within:border-gray-400':
              editingContent,
          }"
        >
          <CommentEditor
            :value="discussion.content"
            @change="discussion.content = $event"
            :submitButtonProps="{
              onClick: () => {
                $resources.discussion.setValue.submit({
                  content: discussion.content,
                })
                editingContent = false
              },
              loading: $resources.discussion.setValue.loading,
            }"
            :discardButtonProps="{
              onClick: () => {
                editingContent = false
                $resources.discussion.reload()
              },
            }"
            :editable="editingContent"
          />
        </div>
        <div class="mt-3">
          <Reactions
            doctype="GP Discussion"
            :name="discussion.name"
            v-model:reactions="discussion.reactions"
            :read-only-mode="readOnlyMode"
          />
        </div>
      </div>
      <CommentsArea
        doctype="GP Discussion"
        :name="discussion.name"
        :newCommentsFrom="discussion.last_unread_comment"
        :read-only-mode="readOnlyMode"
        :disable-new-comment="discussion.closed_at"
      />
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
      <RevisionsDialog
        v-model="showRevisionsDialog"
        doctype="GP Discussion"
        :name="discussion.name"
        fieldname="content"
      />
    </div>
  </div>
</template>
<script>
import {
  Autocomplete,
  Dropdown,
  Dialog,
  Tooltip,
  visibilityDirective,
} from 'frappe-ui'
import Reactions from './Reactions.vue'
import CommentsArea from '@/components/CommentsArea.vue'
import CommentEditor from './CommentEditor.vue'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from './UserProfileLink.vue'
import DiscussionMeta from './DiscussionMeta.vue'
import DiscussionBreadcrumbs from './DiscussionBreadcrumbs.vue'
import RevisionsDialog from './RevisionsDialog.vue'
import { focus } from '@/directives'
import { copyToClipboard } from '@/utils'
import { activeTeams } from '@/data/teams'
import { getTeamProjects } from '@/data/projects'

export default {
  name: 'DiscussionView',
  props: ['postId', 'readOnlyMode'],
  directives: {
    visibility: visibilityDirective,
    focus,
  },
  components: {
    TextEditor,
    Reactions,
    CommentsArea,
    Dropdown,
    Dialog,
    Autocomplete,
    UserProfileLink,
    CommentEditor,
    Tooltip,
    DiscussionMeta,
    DiscussionBreadcrumbs,
    RevisionsDialog,
  },
  resources: {
    discussion() {
      return {
        type: 'document',
        doctype: 'GP Discussion',
        name: this.postId,
        realtime: true,
        whitelistedMethods: {
          trackVisit: 'track_visit',
          closeDiscussion: 'close_discussion',
          reopenDiscussion: 'reopen_discussion',
          pinDiscussion: 'pin_discussion',
          unpinDiscussion: 'unpin_discussion',
          moveToProject: {
            method: 'move_to_project',
            validate(params) {
              if (!params.args.project) {
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
          this.updateUrlSlug()
          if (
            !this.$route.query.comment &&
            !this.$route.query.fromSearch &&
            doc.last_unread_comment
          ) {
            this.$router.replace({
              query: { comment: doc.last_unread_comment },
            })
          }

          if (
            this.$route.name === 'ProjectDiscussion' &&
            Number(this.$route.params.postId) === doc.name
          ) {
            this.$resources.discussion.trackVisit.submit()
          }
        },
      }
    },
  },
  data() {
    return {
      editingContent: false,
      editingTitle: false,
      discussionMoveDialog: {
        show: false,
        project: null,
      },
      showRevisionsDialog: false,
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
          name: 'ProjectDiscussion',
          params: {
            teamId: this.discussion.team,
            projectId: this.discussion.project,
            postId: this.discussion.name,
          },
        })
      })
      this.$resources.discussion.moveToProject.reset()
    },
    handleTitleVisibility(visible, entry) {
      this.showNavbar = !visible
    },
    updateUrlSlug() {
      let doc = this.discussion
      if (!this.$route.params.slug || this.$route.params.slug !== doc.slug) {
        this.$router.replace({
          name: 'ProjectDiscussion',
          params: {
            ...this.$route.params,
            slug: doc.slug,
          },
          query: this.$route.query,
        })
      }
    },
    onBackClick() {
      if (this.$router.options.history.state.back) {
        this.$router.back()
      } else {
        this.$router.push({
          name: 'ProjectDiscussions',
          params: {
            teamId: this.discussion.team,
            projectId: this.discussion.project,
          },
        })
      }
    },
  },
  computed: {
    discussion() {
      return this.$resources.discussion.doc
    },
    projectOptions() {
      return activeTeams.value.map((team) => ({
        group: team.title,
        items: getTeamProjects(team.name).map((project) => ({
          label: project.title,
          value: project.name,
        })),
      }))
    },
    actions() {
      return [
        {
          label: 'Edit Title',
          icon: 'edit',
          handler: () => {
            this.editingTitle = true
          },
        },
        {
          label: 'Revisions',
          icon: 'rotate-ccw',
          handler: () => (this.showRevisionsDialog = true),
        },
        {
          label: 'Copy link',
          icon: 'link',
          handler: this.copyLink,
        },
        {
          label: 'Pin discussion...',
          icon: 'arrow-up-left',
          condition: () => !this.discussion.pinned_at,
          handler: () => {
            let project = this.$getDoc('GP Project', this.discussion.project)
            this.$dialog({
              title: 'Pin discussion',
              message: `When a discussion is pinned, it shows up on top of the discussion list in ${project.title}. Do you want to pin this discussion?`,
              icon: { name: 'arrow-up-left', appearance: 'success' },
              actions: [
                {
                  label: 'Pin',
                  handler: ({ close }) =>
                    this.$resources.discussion.pinDiscussion
                      .submit()
                      .then(close),
                  appearance: 'primary',
                },
                {
                  label: 'Cancel',
                },
              ],
            })
          },
        },
        {
          label: 'Unpin discussion...',
          icon: 'arrow-down-left',
          condition: () => this.discussion.pinned_at,
          handler: () => {
            this.$dialog({
              title: 'Unpin discussion',
              message: `Do you want to unpin this discussion?`,
              icon: { name: 'arrow-down-left', appearance: 'success' },
              actions: [
                {
                  label: 'Unpin',
                  handler: ({ close }) =>
                    this.$resources.discussion.unpinDiscussion
                      .submit()
                      .then(close),
                  appearance: 'primary',
                },
                {
                  label: 'Cancel',
                },
              ],
            })
          },
        },
        {
          label: 'Close discussion...',
          icon: 'lock',
          condition: () => !this.discussion.closed_at,
          handler: () => {
            this.$dialog({
              title: 'Close discussion',
              message:
                'When a discussion is closed, commenting is disabled. Anyone can re-open the discussion later. Do you want to close this discussion?',
              icon: { name: 'lock', appearance: 'success' },
              actions: [
                {
                  label: 'Close',
                  handler: ({ close }) =>
                    this.$resources.discussion.closeDiscussion
                      .submit()
                      .then(close),
                  appearance: 'primary',
                },
                {
                  label: 'Cancel',
                },
              ],
            })
          },
        },
        {
          label: 'Re-open discussion...',
          icon: 'unlock',
          condition: () => this.discussion.closed_at,
          handler: () => {
            this.$dialog({
              title: 'Re-open discussion',
              message:
                'Do you want to re-open this discussion? Anyone can comment on it again.',
              icon: { name: 'unlock', appearance: 'success' },
              actions: [
                {
                  label: 'Re-open',
                  handler: ({ close }) =>
                    this.$resources.discussion.reopenDiscussion
                      .submit()
                      .then(close),
                  appearance: 'primary',
                },
                {
                  label: 'Cancel',
                },
              ],
            })
          },
        },
        {
          label: 'Move to...',
          icon: 'log-out',
          handler: () => {
            this.discussionMoveDialog.show = true
          },
        },
      ]
    },
  },
  pageMeta() {
    if (!this.discussion) return
    let project = this.$getDoc('GP Project', this.discussion.project)
    if (!project) return
    return {
      title: [this.discussion.title, project.title].filter(Boolean).join(' - '),
      emoji: project.icon,
    }
  },
}
</script>
