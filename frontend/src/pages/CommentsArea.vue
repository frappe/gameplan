<template>
  <div class="flex flex-col" ref="comments">
    <div
      v-if="$resources.comments.data == null"
      class="flex animate-pulse items-start space-x-3 px-2 py-4 text-base"
    >
      <div class="h-8 w-8 rounded-full bg-gray-200"></div>
      <div>
        <div class="flex h-8 flex-col justify-center">
          <div class="h-2 w-40 bg-gray-200"></div>
        </div>
        <div class="flex flex-col gap-2">
          <div v-for="i in 4">
            <div
              class="h-2 bg-gray-200"
              :style="{ width: `${Math.max(Math.random() * 800, 600)}px` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    <div class="px-1 pb-20" v-if="$resources.comments.data?.length">
      <template
        v-for="(comment, i) in $resources.comments.data"
        :key="comment.name"
      >
        <div
          class="relative my-4"
          v-if="newMessagesFrom && newMessagesFrom == comment.name"
        >
          <div class="border-b-2 border-blue-600/50"></div>
          <span
            class="absolute -top-2 left-1/2 -translate-x-1/2 bg-white px-2 text-sm font-medium text-blue-700"
          >
            new comments
          </span>
        </div>
        <div
          class="group rounded-md px-1 py-6 transition-shadow"
          :class="{
            ring: !comment.loading && highlightedComment == comment.name,
            'border-t': !newMessagesFrom || newMessagesFrom != comment.name,
          }"
          :data-id="comment.name"
          :ref="'comment-' + comment.name"
        >
          <UserInfo :email="comment.owner" v-slot="{ user }">
            <div class="mb-2 flex items-center text-base text-gray-900">
              <UserProfileLink class="mr-3" :user="user.name">
                <Avatar
                  class="sticky top-1 flex-shrink-0"
                  :label="user.full_name"
                  :imageURL="user.user_image"
                />
              </UserProfileLink>
              <UserProfileLink
                class="font-medium hover:text-blue-600"
                :user="user.name"
              >
                {{ user.full_name }}&nbsp;&middot;&nbsp;
              </UserProfileLink>
              <time
                class="text-gray-600"
                :datetime="comment.creation"
                :title="$dayjs(comment.creation)"
              >
                {{ $dayjs(comment.creation).fromNow() }}
              </time>
              <template v-if="comment.modified > comment.creation">
                <span class="text-gray-600" :title="$dayjs(comment.modified)">
                  &nbsp;&middot; Edited
                </span>
              </template>
              <template v-if="comment.loading">
                &nbsp;&middot;
                <span class="italic text-gray-600">Sending...</span>
              </template>
              <template v-if="comment.error">
                <div>
                  &nbsp;&middot;
                  <span class="text-red-600"> Error</span>
                </div>
              </template>
              <Dropdown
                v-show="!comment.editing"
                class="ml-auto"
                placement="right"
                :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
                :options="[
                  {
                    label: 'Edit',
                    icon: 'edit',
                    handler: () => (comment.editing = true),
                    condition: () =>
                      $isSessionUser(comment.owner) && !comment.deleted_at,
                  },
                  {
                    label: 'Copy link',
                    icon: 'link',
                    handler: () => copyLink(comment),
                  },
                  {
                    label: 'Delete',
                    icon: 'trash',
                    handler: () => {
                      $resources.comments.setValue.submit({
                        name: comment.name,
                        deleted_at: $dayjs().format('YYYY-MM-DD HH:mm:ss'),
                      })
                    },
                    condition: () =>
                      $isSessionUser(comment.owner) &&
                      comment.deleted_at == null,
                  },
                ]"
              />
            </div>
            <div class="flex-1">
              <div
                :class="
                  comment.editing &&
                  'mt-1 min-h-[2.5rem] w-full rounded-lg border bg-white px-3.5 py-1 focus-within:border-gray-400'
                "
                @keydown.ctrl.enter.capture.stop="editComment(comment)"
                @keydown.meta.enter.capture.stop="editComment(comment)"
              >
                <TextEditor
                  v-if="comment.deleted_at == null"
                  editor-class="prose-sm"
                  :editable="comment.editing || false"
                  :content="comment.content"
                  @change="(val) => (comment.content = val)"
                  :starterkit-options="{ heading: { levels: [2, 3, 4, 5, 6] } }"
                  :bubbleMenu="true"
                />
                <span class="text-base italic text-gray-600" v-else>
                  This message is deleted
                </span>
                <div
                  class="mt-3"
                  v-if="!comment.deleted_at && !comment.editing"
                >
                  <Reactions
                    doctype="Team Comment"
                    :name="comment.name"
                    v-model:reactions="comment.reactions"
                  />
                </div>
              </div>
              <div class="space-x-2 pt-2" v-show="comment.editing">
                <Button appearance="primary" @click="editComment(comment)">
                  Save
                </Button>
                <Button appearance="white" @click="comment.editing = false">
                  Discard
                </Button>
              </div>
            </div>
          </UserInfo>
        </div>
      </template>
    </div>

    <div
      v-if="!$readOnlyMode"
      class="sticky bottom-0 mt-2 bg-white py-4 sm:p-2"
      ref="addComment"
    >
      <button
        class="flex w-full items-center rounded-lg bg-gray-100 py-2 px-2 text-left text-base text-gray-600 hover:bg-gray-200"
        @click="showCommentBox = true"
        v-show="!showCommentBox"
      >
        <Avatar
          class="mr-3 flex-shrink-0"
          :label="$user().full_name"
          :imageURL="$user().user_image"
          size="sm"
        />
        Add a comment
      </button>
      <div
        v-show="showCommentBox"
        class="w-full rounded-lg border bg-white p-4 focus-within:border-gray-400"
        @keydown.ctrl.enter.capture.stop="submitComment"
        @keydown.meta.enter.capture.stop="submitComment"
      >
        <div class="mb-4 flex items-center space-x-2">
          <Avatar
            class="flex-shrink-0"
            :label="$user().full_name"
            :imageURL="$user().user_image"
            size="sm"
          />
          <span class="text-base font-medium text-gray-900">
            {{ $user().full_name }}
          </span>
        </div>
        <TextEditor
          ref="newCommentEditor"
          editor-class="min-h-[4rem] prose-sm overflow-y-auto max-h-[50vh]"
          :content="newComment"
          @change="onNewCommentChange"
          :starterkit-options="{ heading: { levels: [2, 3, 4, 5, 6] } }"
          placeholder="Add comment..."
        >
          <template v-slot:bottom>
            <div
              class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center"
            >
              <TextEditorFixedMenu
                class="overflow-x-auto"
                :buttons="textEditorMenuButtons"
              />
              <div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
                <Button @click="discardDialog = true"> Discard </Button>
                <Button
                  appearance="primary"
                  @click="submitComment"
                  :loading="$resources.comments.insert.loading"
                  :disabled="commentEmpty"
                >
                  Submit
                </Button>
              </div>
            </div>
          </template>
        </TextEditor>
      </div>
    </div>
    <Dialog
      :options="{
        title: 'Discard comment',
        message: 'Are you sure you want to discard your comment?',
        actions: [
          {
            label: 'Discard comment',
            handler: () => {
              resetCommentState()
              discardDialog = false
            },
            appearance: 'primary',
          },
          {
            label: 'Keep comment',
            appearance: 'white',
          },
        ],
      }"
      v-model="discardDialog"
    >
    </Dialog>
  </div>
</template>
<script>
import { Avatar, LoadingIndicator, Dropdown, Dialog } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'
import { copyToClipboard } from '@/utils'
import Reactions from '@/components/Reactions.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'
import { nextTick } from 'vue'
import TextEditorMenu from 'frappe-ui/src/components/TextEditor/Menu.vue'
import TextEditorFixedMenu from 'frappe-ui/src/components/TextEditor/TextEditorFixedMenu.vue'
import { getScrollParent } from '@/utils'

export default {
  name: 'CommentsArea',
  props: ['doctype', 'name', 'newCommentsFrom'],
  components: {
    Avatar,
    LoadingIndicator,
    TextEditor,
    Dropdown,
    Reactions,
    UserProfileLink,
    TextEditorMenu,
    TextEditorFixedMenu,
    Dialog,
  },
  data() {
    let draftComment = localStorage.getItem(this.draftCommentKey())
    return {
      commentMap: {},
      showCommentBox: draftComment ? true : false,
      newComment: draftComment || '',
      newMessagesFrom: this.newCommentsFrom,
      highlightedComment: '',
      discardDialog: false,
    }
  },
  watch: {
    showCommentBox(val) {
      if (val) {
        nextTick(() => {
          this.$refs.newCommentEditor.editor.commands.focus()
          // scroll to bottom
          let scrollContainer = getScrollParent(this.$refs.comments)
          scrollContainer.scrollTop = scrollContainer.scrollHeight
        })
      }
    },
  },
  resources: {
    comments() {
      return {
        type: 'list',
        doctype: 'Team Comment',
        fields: [
          'content',
          'owner',
          'creation',
          'modified',
          'name',
          'deleted_at',
        ],
        transform(data) {
          for (let d of data) {
            this.commentMap[d.name] = d
            d.reactions = []
          }
          return data
        },
        filters: {
          reference_doctype: this.doctype,
          reference_name: this.name,
        },
        order_by: 'creation asc',
        limit: 99999,
        onSuccess(comments) {
          setTimeout(() => {
            if (this.$route.query.comment) {
              this.scrollToComment(Number(this.$route.query.comment))
            } else {
              this.scrollToComment(comments[comments.length - 1]?.name)
            }
          }, 300)
          this.attachReactionsToComments()
        },
      }
    },
    reactions() {
      if (!this.$resources.comments.data?.length) return
      let comments = this.$resources.comments.data.map((d) => d.name)
      return {
        type: 'list',
        doctype: 'Team Reaction',
        fields: ['user', 'emoji', 'parent'],
        filters: {
          parenttype: 'Team Comment',
          parent: ['in', comments],
        },
        parent: 'Team Comment',
        order_by: 'parent asc, idx asc',
        limit: 99999,
        onSuccess() {
          this.attachReactionsToComments()
        },
      }
    },
  },
  methods: {
    submitComment() {
      if (this.commentEmpty) {
        return
      }
      this.$resources.comments.setData((data) => {
        data.push({
          owner: this.$user().name,
          content: this.newComment,
          reference_doctype: this.doctype,
          reference_name: this.name,
          loading: true,
          reactions: [],
        })
        return data
      })
      this.$resources.comments.insert.submit({
        reference_doctype: this.doctype,
        reference_name: this.name,
        content: this.newComment,
      })
      this.resetCommentState()
    },
    editComment(comment) {
      comment.loading = true
      comment.editing = false
      this.$resources.comments.setValue.submit(
        {
          name: comment.name,
          content: comment.content,
        },
        {
          onError() {
            comment.loading = false
            comment.error = true
          },
        }
      )
    },
    scrollToComment(comment) {
      if (!comment) return
      this.$nextTick(() => {
        let $comment = this.$refs['comment-' + comment][0]
        if ($comment?.scrollIntoView) {
          $comment.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest',
          })
        }
        this.highlightedComment = comment
        setTimeout(() => (this.highlightedComment = null), 10000)
      })
    },
    copyLink(comment) {
      let location = window.location
      let url = `${location.origin}${location.pathname}?comment=${comment.name}`
      copyToClipboard(url)
    },
    attachReactionsToComments() {
      if (!this.$resources.reactions?.data) return
      for (let d of this.$resources.comments.data) {
        this.commentMap[d.name] = d
        d.reactions = []
      }
      for (let reaction of this.$resources.reactions.data) {
        let comment = this.commentMap[reaction.parent]
        if (comment) {
          comment.reactions.push({
            user: reaction.user,
            emoji: reaction.emoji,
          })
        }
      }
    },
    onNewCommentChange(content) {
      this.newComment = content

      // save draft comment to local storage
      setTimeout(() => {
        // set timeout to move it off main thread
        localStorage.setItem(this.draftCommentKey(), content)
      }, 0)
    },
    resetCommentState() {
      this.newComment = ''
      this.showCommentBox = false
      localStorage.removeItem(this.draftCommentKey())
    },
    draftCommentKey() {
      return `draft-comment-${this.doctype}-${this.name}`
    },
  },
  computed: {
    commentEmpty() {
      return !this.newComment || this.newComment === '<p></p>'
    },
    editorObject() {
      return this.$refs.newCommentEditor?.editor
    },
    textEditorMenuButtons() {
      return [
        'Paragraph',
        ['Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Heading 6'],
        'Separator',
        'Bold',
        'Italic',
        'Separator',
        'Bullet List',
        'Numbered List',
        'Separator',
        'Align Left',
        'Align Center',
        'Align Right',
        'Separator',
        'Image',
        'Link',
        'Blockquote',
        'Code',
        'Horizontal Rule',
        [
          'InsertTable',
          'AddColumnBefore',
          'AddColumnAfter',
          'DeleteColumn',
          'AddRowBefore',
          'AddRowAfter',
          'DeleteRow',
          'MergeCells',
          'SplitCell',
          'ToggleHeaderColumn',
          'ToggleHeaderRow',
          'ToggleHeaderCell',
          'DeleteTable',
        ],
        'Separator',
        'Undo',
        'Redo',
      ]
    },
  },
}

function scrollToElement(element) {
  let headerOffset = 65
  let elementPosition = element.getBoundingClientRect().top
  let offsetPosition = elementPosition + window.pageYOffset - headerOffset
  window.scrollTo({
    top: offsetPosition,
    behavior: 'smooth',
  })
}
</script>
