<template>
  <div class="relative flex h-full flex-col" v-if="postId && discussion">
    <div class="mx-auto w-full max-w-3xl">
      <div class="pb-16">
        <div class="pb-4 pt-16 flex w-full items-center sticky top-0 z-[1] bg-surface-white">
          <UserProfileLink class="mr-3" :user="discussion.owner">
            <UserAvatar :user="discussion.owner" />
          </UserProfileLink>
          <div class="flex flex-col md:block">
            <UserProfileLink
              class="text-base font-medium text-ink-gray-9 hover:text-ink-blue-3"
              :user="discussion.owner"
            >
              {{ $user(discussion.owner).full_name }}
              <span class="hidden md:inline text-ink-gray-8">&nbsp;&middot;&nbsp;</span>
            </UserProfileLink>
            <time
              class="text-base text-ink-gray-5"
              :datetime="discussion.creation"
              :title="$dayjs(discussion.creation)"
            >
              {{ $dayjs(discussion.creation).fromNow() }}
            </time>
          </div>
          <div class="ml-auto flex space-x-2">
            <Dropdown
              v-if="!readOnlyMode"
              class="ml-auto"
              placement="right"
              :button="{
                icon: 'more-horizontal',
                variant: 'ghost',
                label: 'Discussion Options',
              }"
              :options="actions"
            />
          </div>
        </div>
        <div class="pb-4">
          <div class="flex items-start justify-between space-x-1">
            <div v-if="editingTitle" class="w-full">
              <div class="mb-2">
                <input
                  v-if="editingTitle"
                  type="text"
                  class="w-full rounded border-0 bg-surface-gray-2 text-ink-gray-9 px-2 py-1 text-xl font-semibold focus:ring-0"
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
                <p class="mt-1 text-sm text-ink-gray-5">
                  Edit title and press enter. Press escape to cancel.
                </p>
              </div>
            </div>
            <h1 v-else class="flex items-center text-2xl font-semibold">
              <Tooltip v-if="discussion.closed_at" text="This discussion is closed">
                <LucideLock class="mr-2 h-4 w-4 text-ink-gray-7" :stroke-width="2" />
              </Tooltip>
              <span class="text-ink-gray-9">
                {{ discussion.title }}
              </span>
            </h1>
          </div>
          <div class="mt-2 flex items-center text-base" v-show="!editingTitle">
            <DiscussionBreadcrumbs :discussion="discussion" />
            <span class="px-1.5 text-ink-gray-8">&middot;</span>
            <span class="text-ink-gray-5">
              {{
                discussion.participants_count == 1
                  ? `1 participant`
                  : `${discussion.participants_count} participants`
              }}
            </span>
          </div>
        </div>
        <div
          :class="{
            'rounded-lg border p-4 focus-within:border-outline-gray-3': editingContent,
          }"
        >
          <CommentEditor
            :value="discussion.content"
            @change="discussion.content = $event"
            :submitButtonProps="{
              variant: 'solid',
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
          <ErrorMessage class="mt-2" :message="$resources.discussion.moveToProject.error" />
        </template>
        <template #actions>
          <Button
            class="w-full"
            variant="solid"
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
import { Autocomplete, Dropdown, Dialog, Tooltip, call } from 'frappe-ui'
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
            !this.$route.query.poll &&
            !this.$route.query.fromSearch &&
            (doc.last_unread_comment || doc.last_unread_poll)
          ) {
            this.$router.replace({
              query: {
                comment: doc.last_unread_comment || undefined,
                poll: doc.last_unread_poll || undefined,
              },
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
    bookmark() {
      return {
        type: 'resource',
        url: 'gameplan.api.check_bookmark',
        params: {
          discussionId: this.postId,
        },
        auto: true,
        onSuccess(data) {
          this.bookmarkStatus = data
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
      bookmarkStatus: false,
    }
  },
  methods: {
    bookMarkDiscussion() {
      let data = {
        discussion: this.discussion.name,
        remove_bookmark: this.bookmarkStatus,
      }
      call('gameplan.api.bookmark_discussion', { data }).then((res) => {
        this.$resources.bookmark.submit()
      })
    },
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
          onClick: () => {
            this.editingTitle = true
          },
        },
        {
          label: 'Edit Post',
          icon: 'edit',
          onClick: () => {
            this.editingContent = true
          },
        },
        {
          label: 'Revisions',
          icon: 'rotate-ccw',
          onClick: () => (this.showRevisionsDialog = true),
        },
        {
          label: 'Copy link',
          icon: 'link',
          onClick: this.copyLink,
        },
        {
          label: 'Pin discussion...',
          icon: 'arrow-up-left',
          condition: () => !this.discussion.pinned_at,
          onClick: () => {
            let project = this.$getDoc('GP Project', this.discussion.project)
            this.$dialog({
              title: 'Pin discussion',
              message: `When a discussion is pinned, it shows up on top of the discussion list in ${project.title}. Do you want to pin this discussion?`,
              icon: { name: 'arrow-up-left' },
              actions: [
                {
                  label: 'Pin',
                  onClick: (close) => this.$resources.discussion.pinDiscussion.submit().then(close),
                  variant: 'solid',
                },
              ],
            })
          },
        },
        {
          label: 'Unpin discussion...',
          icon: 'arrow-down-left',
          condition: () => this.discussion.pinned_at,
          onClick: () => {
            this.$dialog({
              title: 'Unpin discussion',
              message: `Do you want to unpin this discussion?`,
              icon: { name: 'arrow-down-left' },
              actions: [
                {
                  label: 'Unpin',
                  onClick: (close) =>
                    this.$resources.discussion.unpinDiscussion.submit().then(close),
                  variant: 'solid',
                },
              ],
            })
          },
        },
        {
          label: 'Close discussion...',
          icon: 'lock',
          condition: () => !this.discussion.closed_at,
          onClick: () => {
            this.$dialog({
              title: 'Close discussion',
              message:
                'When a discussion is closed, commenting is disabled. Anyone can re-open the discussion later. Do you want to close this discussion?',
              icon: { name: 'lock' },
              actions: [
                {
                  label: 'Close',
                  onClick: (close) =>
                    this.$resources.discussion.closeDiscussion.submit().then(close),
                  variant: 'solid',
                },
              ],
            })
          },
        },
        {
          label: 'Re-open discussion...',
          icon: 'unlock',
          condition: () => this.discussion.closed_at,
          onClick: () => {
            this.$dialog({
              title: 'Re-open discussion',
              message: 'Do you want to re-open this discussion? Anyone can comment on it again.',
              icon: { name: 'unlock' },
              actions: [
                {
                  label: 'Re-open',
                  onClick: (close) =>
                    this.$resources.discussion.reopenDiscussion.submit().then(close),
                  variant: 'solid',
                },
              ],
            })
          },
        },
        {
          label: `${this.bookmarkStatus ? 'Remove Bookmark' : 'Add Bookmark'}`,
          icon: 'bookmark',
          onClick: this.bookMarkDiscussion,
        },
        {
          label: 'Move to...',
          icon: 'log-out',
          onClick: () => {
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
