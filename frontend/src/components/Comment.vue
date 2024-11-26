<template>
  <div
    class="pb-16 transition-shadow"
    :class="{
      ring: !comment.loading && highlight,
    }"
    :data-id="comment.name"
  >
    <UserInfo :email="comment.owner" v-slot="{ user }">
      <div
        class="flex items-center text-base text-ink-gray-9 sticky top-0 pt-16 pb-4 bg-surface-white z-[1]"
      >
        <UserProfileLink class="mr-3" :user="user.name">
          <UserAvatar size="lg" :user="user.name" />
        </UserProfileLink>
        <div class="md:flex md:items-center">
          <UserProfileLink class="font-medium hover:text-ink-blue-3" :user="user.name">
            {{ user.full_name }}
            <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
          </UserProfileLink>
          <div>
            <time
              class="text-ink-gray-5"
              :datetime="comment.creation"
              :title="$dayjs(comment.creation)"
            >
              {{ $dayjs(comment.creation).fromNow() }}
            </time>
            <span
              v-if="comment.modified > comment.creation"
              class="text-ink-gray-5"
              :title="$dayjs(comment.modified)"
            >
              &nbsp;&middot; Edited
            </span>
            <span v-if="comment.loading" class="italic text-ink-gray-5">
              &nbsp;&middot; Sending...
            </span>
            <div v-if="comment.error">
              &nbsp;&middot;
              <span class="text-ink-red-4"> Error</span>
            </div>
          </div>
        </div>
        <Dropdown
          v-show="!comment.editing"
          class="ml-auto"
          placement="right"
          :button="{
            icon: 'more-horizontal',
            variant: 'ghost',
            label: 'Comment Options',
          }"
          :options="[
            {
              label: 'Edit',
              icon: 'edit',
              onClick: () => (comment.editing = true),
              condition: () => !comment.deleted_at && !readOnlyMode,
            },
            {
              label: 'Revisions',
              icon: 'rotate-ccw',
              onClick: () => (showRevisionsDialog = true),
              condition: () => comment.modified > comment.creation,
            },
            {
              label: 'Copy link',
              icon: 'link',
              onClick: () => copyLink(comment),
            },
            {
              label: 'Delete',
              icon: 'trash',
              onClick: () => {
                $dialog({
                  title: 'Delete comment',
                  message: 'Are you sure you want to delete this comment?',
                  actions: [
                    {
                      label: 'Delete',
                      variant: 'solid',
                      theme: 'red',
                      onClick: (close) => {
                        return comments.setValue
                          .submit({
                            name: comment.name,
                            deleted_at: $dayjs().format('YYYY-MM-DD HH:mm:ss'),
                          })
                          .then(close)
                      },
                    },
                  ],
                })
              },
              condition: () =>
                $isSessionUser(comment.owner) && comment.deleted_at == null && !readOnlyMode,
            },
          ]"
        />
      </div>
      <div class="flex-1">
        <div
          :class="{
            'w-full rounded-lg border bg-surface-white p-4 focus-within:border-outline-gray-3':
              comment.editing,
          }"
          @keydown.ctrl.enter.capture.stop="editComment(comment)"
          @keydown.meta.enter.capture.stop="editComment(comment)"
        >
          <CommentEditor
            v-if="comment.deleted_at == null"
            :value="comment.content"
            @change="comment.content = $event"
            :editable="comment.editing || false"
            :submitButtonProps="{
              onClick: () => editComment(comment),
              loading: comment.loading,
            }"
            :discardButtonProps="{
              onClick: () => {
                comment.editing = false
                comments.fetchOne.submit(comment.name)
              },
            }"
          />
          <span class="text-base italic text-ink-gray-5" v-else> This message is deleted </span>
          <div class="mt-3" v-if="!comment.deleted_at && !comment.editing && comment.reactions">
            <Reactions
              doctype="GP Comment"
              :name="comment.name"
              v-model:reactions="comment.reactions"
              :read-only-mode="readOnlyMode"
            />
          </div>
        </div>
      </div>
    </UserInfo>
    <RevisionsDialog
      v-model="showRevisionsDialog"
      doctype="GP Comment"
      :name="comment.name"
      fieldname="content"
    />
  </div>
</template>
<script>
import { Dropdown } from 'frappe-ui'
import { copyToClipboard } from '@/utils'
import UserProfileLink from './UserProfileLink.vue'
import CommentEditor from './CommentEditor.vue'
import Reactions from './Reactions.vue'
import RevisionsDialog from './RevisionsDialog.vue'

export default {
  name: 'Comment',
  props: {
    comment: {
      type: Object,
      required: true,
    },
    readOnlyMode: {
      type: Boolean,
      default: false,
    },
    highlight: {
      type: Boolean,
      default: false,
    },
    comments: {
      type: Object,
    },
  },
  components: {
    UserProfileLink,
    Dropdown,
    CommentEditor,
    Reactions,
    RevisionsDialog,
  },
  data() {
    return {
      showRevisionsDialog: false,
    }
  },
  methods: {
    editComment(comment) {
      comment.loading = true
      comment.editing = false
      this.comments.setValue.submit(
        {
          name: comment.name,
          content: comment.content,
        },
        {
          onSuccess() {
            comment.loading = false
          },
          onError(error) {
            comment.loading = false
            comment.error = error
          },
        },
      )
    },
    copyLink(comment) {
      let location = window.location
      let url = `${location.origin}${location.pathname}?comment=${comment.name}`
      copyToClipboard(url)
    },
  },
}
</script>
