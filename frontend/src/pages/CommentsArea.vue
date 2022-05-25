<template>
  <div class="flex flex-col justify-between px-5 pt-6" ref="comments">
    <div class="space-y-6">
      <div
        class="flex items-start space-x-3 group"
        v-for="(comment, i) in $resources.comments.data"
        :key="comment.name"
      >
        <UserInfo :email="comment.owner" v-slot="{ user }">
          <Avatar
            class="flex-shrink-0"
            :label="user.full_name"
            :imageURL="user.user_image"
          />
          <div class="flex-1">
            <div class="text-base text-gray-900">
              <span class="font-medium">
                {{ user.full_name }}
              </span>
              &middot;
              <time
                class="text-gray-600"
                :datetime="comment.creation"
                :title="$dayjs(comment.creation)"
              >
                {{ $dayjs(comment.creation).fromNow() }}
              </time>

              <template v-if="comment.modified > comment.creation">
                &middot;
                <span class="italic text-gray-600">Edited</span>
              </template>
              <template v-if="comment.loading">
                &middot;
                <span class="italic text-gray-600">Sending...</span>
              </template>
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
                editor-class="prose-p:text-base"
                :editable="comment.editing || false"
                :content="comment.content"
                @change="(val) => (comment.content = val)"
                :starterkit-options="{ heading: false }"
              />
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
          <div
            class="!ml-auto"
            :class="comment.editing ? '' : 'opacity-0 group-hover:opacity-100'"
          >
            <Button
              v-show="!comment.editing"
              icon="edit-2"
              appearance="minimal"
              @click="comment.editing = true"
            />
          </div>
        </UserInfo>
      </div>
    </div>

    <div
      class="sticky bottom-0 flex items-center pt-6 pb-6 space-x-3 bg-gray-50"
      ref="addComment"
    >
      <Avatar
        class="flex-shrink-0"
        :label="$user().full_name"
        :imageURL="$user().user_image"
      />
      <div class="relative flex items-center w-full">
        <div
          class="relative w-full border focus-within:border-gray-400 bg-white rounded-lg px-3.5 py-1 min-h-[2.5rem]"
          @keydown.ctrl.enter.capture.stop="submitComment"
          @keydown.meta.enter.capture.stop="submitComment"
        >
          <span
            class="pointer-events-none absolute py-1.5 text-base text-gray-600"
            v-if="commentEmpty"
          >
            Add comment...
          </span>
          <TextEditor
            editor-class="prose-p:text-base"
            :content="newComment"
            @change="(val) => (newComment = val)"
            :starterkit-options="{ heading: false }"
          />
        </div>
      </div>
      <button
        v-if="!commentEmpty"
        class="grid flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full place-items-center"
        @click="submitComment"
        :disabled="$resources.comments.insert.loading"
      >
        <LoadingIndicator
          class="w-4 h-4 text-white"
          v-if="$resources.comments.insert.loading"
        />
        <FeatherIcon
          v-else
          class="w-4 h-4 text-white"
          name="arrow-up"
          :stroke-width="2"
        />
      </button>
    </div>
  </div>
</template>
<script>
import { Avatar, LoadingIndicator, TextEditor } from 'frappe-ui'

export default {
  name: 'CommentsArea',
  props: ['task'],
  components: { Avatar, LoadingIndicator, TextEditor },
  data() {
    return {
      newComment: '',
    }
  },
  resources: {
    comments() {
      return {
        type: 'list',
        doctype: 'Team Comment',
        fields: ['content', 'owner', 'creation', 'modified', 'name'],
        filters: {
          task: this.task.doc.name,
        },
        order_by: 'creation asc',
        onSuccess() {
          this.scrollToLastComment()
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
          task: this.task.doc.name,
          loading: true,
        })
        return data
      })
      this.$resources.comments.insert.submit(
        {
          task: this.task.doc.name,
          content: this.newComment,
        },
        {
          onSuccess() {
            this.scrollToLastComment()
          },
        }
      )
      this.newComment = ''
    },
    editComment(comment) {
      comment.loading = true
      comment.editing = false
      this.$resources.comments.setValue.submit({
        name: comment.name,
        content: comment.content,
      })
    },
    scrollToLastComment() {
      this.$nextTick(() => {
        this.$refs.comments.scrollTop = this.$refs.comments.scrollHeight
      })
    },
  },
  computed: {
    commentEmpty() {
      return !this.newComment || this.newComment === '<p></p>'
    },
  },
}
</script>
