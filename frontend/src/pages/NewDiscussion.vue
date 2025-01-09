<template>
  <PageHeader>
    <Breadcrumbs
      class="h-7"
      :items="[{ label: 'New Discussion', route: { name: 'NewDiscussion' } }]"
    />
  </PageHeader>
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
          <Autocomplete
            v-model="selectedSpace"
            :options="spaceOptions"
            placeholder="Select Space"
          />
        </div>
        <div class="hidden shrink-0 space-x-2 sm:block">
          <Button @click="discard">Discard</Button>
          <Button variant="solid" :loading="discussions.insert.loading" @click="publish">
            Publish
          </Button>
        </div>
      </div>
      <ErrorMessage :message="errorMessage || discussions.insert.error" />
      <textarea
        class="mt-1 w-full resize-none border-0 px-0 py-0.5 text-3xl font-bold placeholder-gray-400 focus:ring-0"
        v-model="draftDiscussion.title"
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
        ref="textEditorRef"
        class="mt-1"
        editor-class="rounded-b-lg max-w-[unset] prose-sm h-[calc(100vh-340px)] sm:h-[calc(100vh-250px)] overflow-auto"
        :content="draftDiscussion.content"
        @change="draftDiscussion.content = $event"
        placeholder="Write something..."
      >
        <template v-slot:bottom>
          <div class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center">
            <TextEditorFixedMenu class="overflow-x-auto" :buttons="textEditorMenuButtons" />
            <div class="mt-2 shrink-0 space-x-2 text-right sm:hidden">
              <Button @click="discard">Discard</Button>
              <Button variant="solid" :loading="discussions.insert.loading" @click="publish">
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
import { computed, onMounted, ref, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Autocomplete, Breadcrumbs, TextEditorFixedMenu } from 'frappe-ui'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { useSessionUser } from '@/data/users'
import PageHeader from '@/components/PageHeader.vue'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'
import { focus as vFocus } from '@/directives'
import { createDialog } from '@/utils/dialogs'
import { useLocalStorage } from '@vueuse/core'
import { GPDiscussion } from '@/types/doctypes'

const currentRoute = useRoute()
const sessionUser = useSessionUser()
const router = useRouter()

const groupedSpaces = useGroupedSpaces({ filterFn: (space) => !space.archived_at })
const selectedSpace = ref<{ label: string; value: string } | null>(null)
const textEditorRef = useTemplateRef('textEditorRef')
const discussions = useDoctype<GPDiscussion>('GP Discussion')
const errorMessage = ref<string | null>(null)

const draftDiscussion = useLocalStorage(
  'newDiscussion',
  {
    title: '',
    content: '',
  },
  { deep: true },
)

const spaceOptions = computed(() => {
  return groupedSpaces.value.map((group) => {
    return {
      group: group.title,
      items: group.spaces.map((space) => ({
        label: space.title,
        value: space.name,
      })),
    }
  })
})

onMounted(() => {
  if (currentRoute.query?.spaceId) {
    let spaceOption = spaceOptions.value
      .map((group) => group.items)
      .flat()
      .find((space) => space.value.toString() === currentRoute.query.spaceId)
    if (spaceOption) {
      selectedSpace.value = spaceOption
    }
  }
})

function publish() {
  if (!draftDiscussion.value.title) {
    errorMessage.value = 'Please enter title before publishing.'
    return
  }
  if (!selectedSpace.value) {
    errorMessage.value = 'Please select a space before publishing.'
    return
  }
  errorMessage.value = null

  return discussions.insert
    .submit({
      project: selectedSpace.value?.value,
      title: draftDiscussion.value.title,
      content: draftDiscussion.value.content,
    })
    .then((doc) => {
      router.replace({
        name: 'Discussion',
        params: {
          spaceId: doc.project,
          postId: doc.name,
        },
      })
      resetValues()
    })
}

function resetValues() {
  selectedSpace.value = null
  draftDiscussion.value.title = ''
  draftDiscussion.value.content = ''
}

function discard() {
  if (!textEditorRef.value.editor.isEmpty || draftDiscussion.value.title) {
    createDialog({
      title: 'Discard post',
      message: 'Are you sure you want to discard your post?',
      actions: [
        {
          label: 'Discard post',
          onClick: ({ close }) => {
            resetValues()
            router.back()
            close()
          },
          variant: 'solid',
        },
      ],
    })
  } else {
    router.back()
  }
}

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
</script>
