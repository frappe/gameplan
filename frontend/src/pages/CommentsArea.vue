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
    <div class="space-y-5 px-1 pt-6" v-if="$resources.comments.data?.length">
      <div
        class="group flex items-start space-x-3 rounded-md p-1 transition-shadow"
        :class="{
          ring: !comment.loading && highlightedComment == comment.name,
        }"
        v-for="(comment, i) in $resources.comments.data"
        :key="comment.name"
        :data-id="comment.name"
        :ref="'comment-' + comment.name"
      >
        <UserInfo :email="comment.owner" v-slot="{ user }">
          <UserProfileLink :user="user.name">
            <Avatar
              class="sticky top-1 flex-shrink-0"
              :label="user.full_name"
              :imageURL="user.user_image"
            />
          </UserProfileLink>
          <div class="flex-1">
            <div class="flex items-center text-base text-gray-900">
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
                editor-class="prose-sm prose-p:text-base"
                :editable="comment.editing || false"
                :content="comment.content"
                @change="(val) => (comment.content = val)"
                :starterkit-options="{ heading: { levels: [2, 3, 4, 5, 6] } }"
                :bubbleMenu="true"
              />
              <span class="text-base italic text-gray-600" v-else>
                This message is deleted
              </span>
              <div class="mt-3" v-if="!comment.deleted_at && !comment.editing">
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
    </div>

    <div class="flex items-start space-x-3 px-2 pt-6 pb-6" ref="addComment">
      <Avatar
        class="mt-1 flex-shrink-0"
        :label="$user().full_name"
        :imageURL="$user().user_image"
      />
      <div class="w-full">
        <div
          class="min-h-[2.5rem] w-full rounded-lg border bg-white px-3.5 py-1 focus-within:border-gray-400"
          @keydown.ctrl.enter.capture.stop="submitComment"
          @keydown.meta.enter.capture.stop="submitComment"
        >
          <TextEditor
            editor-class="prose-p:text-base min-h-[4rem] prose-sm"
            :content="newComment"
            @change="(val) => (newComment = val)"
            :starterkit-options="{ heading: { levels: [2, 3, 4, 5, 6] } }"
            placeholder="Add comment..."
            :bubbleMenu="true"
          />
        </div>
        <Button
          class="mt-2"
          v-show="!commentEmpty"
          appearance="primary"
          @click="submitComment"
          :loading="$resources.comments.insert.loading"
        >
          Submit
        </Button>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, LoadingIndicator, Dropdown } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'
import { copyToClipboard } from '@/utils'
import Reactions from '@/components/Reactions.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'

export default {
  name: 'CommentsArea',
  props: ['doctype', 'name'],
  components: {
    Avatar,
    LoadingIndicator,
    TextEditor,
    Dropdown,
    Reactions,
    UserProfileLink,
  },
  data() {
    return {
      commentMap: {},
      newComment: '',
      highlightedComment: '',
    }
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
        onSuccess() {
          if (this.$route.query.comment) {
            this.scrollToComment(Number(this.$route.query.comment))
          }
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
      this.newComment = ''
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
        scrollToElement($comment)
        this.highlightedComment = comment
        setTimeout(() => (this.highlightedComment = null), 2000)
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
  },
  computed: {
    commentEmpty() {
      return !this.newComment || this.newComment === '<p></p>'
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
