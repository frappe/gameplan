<template>
  <header class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5">
    <Breadcrumbs
      class="h-7"
      :items="[{ label: 'New Discussion', route: { name: 'NewDiscussion' } }]"
    />
  </header>
  <div class="mx-auto max-w-4xl pt-4 sm:px-5">
    <div class="rounded-lg border p-4">
      <div class="mb-3 flex items-center space-x-2">
        <UserProfileLink :user="sessionUser.name">
          <UserAvatar size="lg" :user="sessionUser.name" />
        </UserProfileLink>
        <div class="flex w-full items-center">
          <span class="mr-2 text-base text-gray-900">
            <UserProfileLink class="font-medium hover:text-blue-600" :user="sessionUser.name">
              {{ sessionUser.full_name }}
            </UserProfileLink>
            in
          </span>
          <Autocomplete v-model="team" :options="teamOptions" placeholder="Select Team" />
        </div>
        <div class="hidden shrink-0 space-x-2 sm:block">
          <Button @click="discard">Discard</Button>
          <Button variant="solid" :loading="newDiscussion.loading" @click="publish">
            Publish
          </Button>
        </div>
      </div>
      <ErrorMessage :message="newDiscussion.error" />
      <textarea
        class="mt-1 w-full resize-none border-0 px-0 py-0.5 text-3xl font-bold placeholder-gray-400 focus:ring-0"
        v-model="title"
        placeholder="Title"
        rows="1"
        wrap="soft"
        maxlength="140"
        v-focus
        @keydown.enter.prevent="textEditorRef.editor.commands.focus()"
        @input="
          (e) => {
            e.target.style.height = e.target.scrollHeight + 'px'
          }
        "
      ></textarea>
      <TextEditor
        :ref="textEditorRef"
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
              <Button variant="solid" :loading="newDiscussion.loading" @click="publish">
                Publish
              </Button>
            </div>
          </div>
        </template>
      </TextEditor>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Autocomplete, Breadcrumbs, createResource, TextEditorFixedMenu } from 'frappe-ui'
import { focus as vFocus } from '@/directives'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'
import router from '@/router'
import { activeTeams } from '@/data/teams'
import { useSessionUser } from '@/data/users'
import { createDialog } from '@/utils/dialogs'

const sessionUser = useSessionUser()
const title = ref('')
const content = ref('')

const team = ref(null)
const teamOptions = computed(() =>
  activeTeams.value.map((team) => ({ label: team.title, value: team.name })),
)
onMounted(() => {
  for (let t of activeTeams.value) {
    if (t.is_default) {
      team.value = t.name
      break
    }
  }
})

const textEditorRef = ref(null)
const textEditorMenuButtons = [
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

const newDiscussion = createResource({
  url: 'frappe.client.insert',
  makeParams({ title, content }) {
    return {
      doc: {
        doctype: 'GP Discussion',
        team: team.value,
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
    router.replace({
      name: 'ProjectDiscussion',
      params: {
        teamId: doc.team,
        projectId: doc.project,
        postId: doc.name,
      },
    })
    title.value = ''
    content.value = ''
  },
})

function onNewPostChange(value) {
  content.value = value
}

function publish() {
  newDiscussion.submit({
    title: title.value,
    content: content.value,
  })
}

function discard() {
  console.log(textEditorRef)
  if (!textEditorRef.editor.isEmpty || this.title) {
    createDialog({
      title: 'Discard post',
      message: 'Are you sure you want to discard your post?',
      actions: [
        {
          label: 'Discard post',
          onClick: (close) => {
            router.push({ name: 'ProjectDiscussions' })
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
    router.push({ name: 'ProjectDiscussions' })
  }
}
</script>
