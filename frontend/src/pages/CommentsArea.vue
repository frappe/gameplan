<template>
  <div class="flex flex-col" ref="comments">
    <div class="px-1 pt-6 space-y-5" v-if="$resources.comments.data?.length">
      <div
        class="flex items-start p-1 space-x-3 transition-shadow rounded-md group"
        :class="{
          ring: !comment.loading && highlightedComment == comment.name,
        }"
        v-for="(comment, i) in $resources.comments.data"
        :key="comment.name"
        :data-id="comment.name"
        :ref="'comment-' + comment.name"
      >
        <UserInfo :email="comment.owner" v-slot="{ user }">
          <Avatar
            class="sticky flex-shrink-0 top-1"
            :label="user.full_name"
            :imageURL="user.user_image"
          />
          <div class="flex-1">
            <div class="flex items-center text-base text-gray-900">
              <span class="font-medium">
                {{ user.full_name }}&middot;&nbsp;</span
              >
              <time
                class="text-gray-600"
                :datetime="comment.creation"
                :title="$dayjs(comment.creation)"
              >
                {{ $dayjs(comment.creation).fromNow() }}
              </time>

              <template v-if="comment.modified > comment.creation">
                &middot;
                <span class="text-gray-600" :title="$dayjs(comment.modified)">
                  Edited
                </span>
              </template>
              <template v-if="comment.loading">
                &middot;
                <span class="italic text-gray-600">Sending...</span>
              </template>
              <template v-if="comment.error">
                &middot;
                <span class="text-red-600">Error</span>
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
                    condition: () => $user().name === comment.owner,
                  },
                  {
                    label: 'Copy link',
                    icon: 'link',
                    handler: () => copyLink(comment),
                  },
                ]"
              />
            </div>
            <div
              :class="
                comment.editing &&
                'mt-1 w-full border focus-within:border-gray-400 bg-white rounded-lg px-3.5 py-1 min-h-[2.5rem]'
              "
              @keydown.ctrl.enter.capture.stop="editComment(comment)"
              @keydown.meta.enter.capture.stop="editComment(comment)"
            >
              <TextEditor
                editor-class="prose-sm prose-p:text-base"
                :editable="comment.editing || false"
                :content="comment.content"
                @change="(val) => (comment.content = val)"
                :starterkit-options="{ heading: false }"
              />
              <div class="mt-3">
                <Reactions
                  doctype="Team Comment"
                  :name="comment.name"
                  v-model:reactions="comment.reactions"
                />
              </div>
            </div>
            <div class="pt-2 space-x-2" v-show="comment.editing">
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

    <div class="flex items-start px-2 pt-6 pb-6 space-x-3" ref="addComment">
      <Avatar
        class="flex-shrink-0 mt-1"
        :label="$user().full_name"
        :imageURL="$user().user_image"
      />
      <div class="w-full">
        <div
          class="w-full border focus-within:border-gray-400 bg-white rounded-lg px-3.5 py-1 min-h-[2.5rem]"
          @keydown.ctrl.enter.capture.stop="submitComment"
          @keydown.meta.enter.capture.stop="submitComment"
        >
          <TextEditor
            editor-class="prose-p:text-base min-h-[4rem] prose-sm"
            :content="newComment"
            @change="(val) => (newComment = val)"
            :starterkit-options="{ heading: false }"
            placeholder="Add comment..."
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

export default {
  name: 'CommentsArea',
  props: ['doctype', 'name'],
  components: { Avatar, LoadingIndicator, TextEditor, Dropdown, Reactions },
  data() {
    return {
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
          'reactions.user as reaction_user',
          'reactions.emoji as reaction_emoji',
        ],
        transform(data) {
          let comments = {}
          let out = []
          for (let d of data) {
            let comment
            if (!comments[d.name]) {
              d.reactions = []
              comments[d.name] = d
              out.push(d)
            }
            comment = comments[d.name]
            if (d.reaction_user && d.reaction_emoji) {
              comment.reactions.push({
                user: d.reaction_user,
                emoji: d.reaction_emoji,
              })
            }
          }
          return out
        },
        filters: {
          reference_doctype: this.doctype,
          reference_name: this.name,
        },
        order_by: 'creation asc',
        limit: 999,
        onSuccess() {
          if (this.$route.query.comment) {
            this.scrollToComment(Number(this.$route.query.comment))
            this.$router.replace({ query: null })
          }
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
        let scrollContainer = getScrollParent($comment)
        scrollContainer.scrollTop =
          $comment.offsetTop - scrollContainer.offsetTop - 2
        this.highlightedComment = comment
        setTimeout(() => (this.highlightedComment = null), 2000)
      })
    },
    copyLink(comment) {
      let location = window.location
      let url = `${location.origin}${location.pathname}?comment=${comment.name}`
      copyToClipboard(url)
    },
  },
  computed: {
    commentEmpty() {
      return !this.newComment || this.newComment === '<p></p>'
    },
  },
}

function getScrollParent(node) {
  if (node == null) {
    return null
  }

  if (node.scrollHeight > node.clientHeight) {
    return node
  } else {
    return getScrollParent(node.parentNode)
  }
}
</script>
