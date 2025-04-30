<template>
  <div class="pt-6">
    <div class="rounded-lg border p-4">
      <div class="mb-3 flex items-center space-x-2">
        <UserProfileLink :user="$user().name">
          <UserAvatar size="lg" :user="$user().name" />
        </UserProfileLink>
        <div class="flex w-full items-center">
          <div>
            <span class="text-base text-ink-gray-8">
              <UserProfileLink class="font-medium hover:text-ink-blue-4" :user="$user().name">
                {{ $user().full_name }}
              </UserProfileLink>
              in
              <router-link
                class="hover:text-ink-blue-4"
                :to="{
                  name: 'Team',
                  params: {
                    teamId: project.doc.team,
                  },
                }"
              >
                {{ $getDoc('GP Team', project.doc.team)?.title || project.doc.team }}
              </router-link>
              <span class="text-ink-gray-4"> &mdash; </span>
              <router-link
                class="hover:text-ink-blue-4"
                :to="{
                  name: 'Project',
                  params: {
                    teamId: project.doc.team,
                    projectId: project.doc.name,
                  },
                }"
              >
                {{ project.doc.title }}
              </router-link>
            </span>
          </div>
        </div>
        <div class="hidden shrink-0 space-x-2 sm:block">
          <Button @click="discard">Discard</Button>
          <Button variant="solid" :loading="$resources.newDiscussion.loading" @click="publish">
            Publish
          </Button>
        </div>
      </div>
      <ErrorMessage :message="$resources.newDiscussion.error" />
      <textarea
        class="mt-1 w-full resize-none border-0 px-0 py-0.5 text-3xl font-bold placeholder-ink-gray-3 focus:ring-0"
        v-model="title"
        placeholder="Title"
        rows="1"
        wrap="soft"
        maxlength="140"
        v-focus
        @keydown.enter.prevent="$refs.textEditor.editor.commands.focus()"
        @input="
          (e) => {
            e.target.style.height = e.target.scrollHeight + 'px'
          }
        "
        @change="(e) => saveDraftPost({ title: e.target.value })"
      ></textarea>
      <TextEditor
        ref="textEditor"
        class="mt-1"
        editor-class="rounded-b-lg max-w-[unset] prose-sm h-[calc(100vh-340px)] sm:h-[calc(100vh-250px)] overflow-auto"
        :content="content"
        @change="onNewPostChange"
        placeholder="Write something..."
      >
        <template v-slot:bottom>
          <div class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center">
            <TextEditorFixedMenu class="overflow-x-auto" :buttons="textEditorMenuButtons" />
            <div class="mt-2 shrink-0 space-x-2 text-right sm:hidden">
              <Button @click="discard">Discard</Button>
              <Button variant="solid" :loading="$resources.newDiscussion.loading" @click="publish">
                Publish
              </Button>
            </div>
          </div>
        </template>
      </TextEditor>
    </div>
  </div>
</template>
<script>
import TextEditor from '@/components/TextEditor.vue'
import { vFocus } from '@/directives'
import UserProfileLink from '@/components/UserProfileLink.vue'
import TextEditorFixedMenu from 'frappe-ui/src/components/TextEditor/TextEditorFixedMenu.vue'

export default {
  name: 'ProjectDiscussionNew',
  props: ['project'],
  components: { TextEditor, UserProfileLink, TextEditorFixedMenu },
  directives: { focus: vFocus },
  data() {
    let draftPost = this.getDraftPost()
    return {
      title: draftPost?.title || '',
      content: draftPost?.content || '',
    }
  },
  resources: {
    newDiscussion() {
      return {
        url: 'frappe.client.insert',
        makeParams({ title, content }) {
          return {
            doc: {
              doctype: 'GP Discussion',
              project: this.project.doc.name,
              title,
              content,
            },
          }
        },
        validate(params) {
          if (!params.doc.title) {
            return `Please enter title before publishing.`
          }
        },
        onSuccess(doc) {
          this.$router.replace({
            name: 'ProjectDiscussion',
            params: {
              teamId: doc.team,
              projectId: doc.project,
              postId: doc.name,
            },
          })
          this.title = ''
          this.content = ''
        },
      }
    },
  },
  methods: {
    onNewPostChange(value) {
      this.content = value
      this.saveDraftPost({ content: value })
    },
    publish() {
      this.$resources.newDiscussion.submit(
        {
          title: this.title,
          content: this.content,
        },
        {
          onSuccess() {
            this.clearDraftPost()
          },
        },
      )
    },
    discard() {
      if (!this.$refs.textEditor.editor.isEmpty || this.title) {
        this.$dialog({
          title: 'Discard post',
          message: 'Are you sure you want to discard your post?',
          actions: [
            {
              label: 'Discard post',
              onClick: (close) => {
                localStorage.removeItem(this.draftPostKey())
                this.$router.push({ name: 'ProjectDiscussions' })
                close()
              },
              variant: 'solid',
            },
            {
              label: 'Keep post',
            },
          ],
        })
      } else {
        localStorage.removeItem(this.draftPostKey())
        this.$router.push({ name: 'ProjectDiscussions' })
      }
    },
    saveDraftPost({ title, content }) {
      setTimeout(() => {
        let draftPost = this.getDraftPost()
        if (!draftPost) {
          draftPost = {}
        }
        if (title != null) {
          draftPost.title = title
        }
        if (content != null) {
          draftPost.content = content
        }
        localStorage.setItem(this.draftPostKey(), JSON.stringify(draftPost))
      }, 0)
    },
    getDraftPost() {
      let draftPost = localStorage.getItem(this.draftPostKey())
      return draftPost ? JSON.parse(draftPost) : null
    },
    clearDraftPost() {
      localStorage.removeItem(this.draftPostKey())
    },
    draftPostKey() {
      return `draft-post-${this.project.doc.name}`
    },
  },
  computed: {
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
        'FontColor',
        'Separator',
        'Image',
        'Video',
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
</script>
