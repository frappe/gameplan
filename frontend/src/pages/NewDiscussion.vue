<template>
  <PageHeader>
    <Breadcrumbs
      class="h-7"
      :items="[
        { label: 'Discussions', route: { name: 'Discussions' } },
        {
          label: draftDoc?.doc ? `${draftDiscussion.title} (Draft)` : 'New Discussion',
          route: { name: 'NewDiscussion' },
        },
      ]"
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
            @update:model-value="updateDraftDebounced"
          />
        </div>
        <div class="hidden shrink-0 space-x-2 sm:block">
          <div class="inline-flex text-ink-gray-5 text-sm" v-if="savingDraft">Saving...</div>
          <Button v-if="draftDoc?.doc" @click="deleteDraft"> Delete </Button>
          <Button v-else @click="discard"> Discard </Button>
          <Button v-if="!draftDoc?.doc" @click="saveDraft" :loading="savingDraft">
            Save as draft
          </Button>
          <Button variant="solid" :loading="publishing" @click="publish"> Publish </Button>
        </div>
      </div>
      <ErrorMessage :message="errorMessage || discussions.insert.error" />
      <textarea
        class="mt-1 w-full resize-none border-0 px-0 py-0.5 text-3xl font-bold placeholder-gray-400 focus:ring-0"
        v-model="draftDiscussion.title"
        @update:model-value="updateDraftDebounced"
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
        @change="
          (content) => {
            draftDiscussion.content = content
            updateDraftDebounced()
          }
        "
        placeholder="Write something..."
      >
        <template v-slot:bottom>
          <div class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center">
            <TextEditorFixedMenu class="overflow-x-auto" :buttons="textEditorMenuButtons" />
            <div class="mt-2 shrink-0 space-x-2 text-right sm:hidden">
              <div class="inline-flex text-ink-gray-5 text-sm" v-if="savingDraft">Saving...</div>
              <Button v-if="draftDoc?.doc" @click="deleteDraft"> Delete </Button>
              <Button v-else @click="discard"> Discard </Button>
              <Button v-if="!draftDoc?.doc" @click="saveDraft" :loading="savingDraft">
                Save as draft
              </Button>
              <Button variant="solid" :loading="publishing" @click="publish"> Publish </Button>
            </div>
          </div>
        </template>
      </TextEditor>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Autocomplete, Breadcrumbs, TextEditorFixedMenu, debounce } from 'frappe-ui'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useDoc, useDoctype, useNewDoc } from 'frappe-ui/src/data-fetching'
import { useSessionUser } from '@/data/users'
import PageHeader from '@/components/PageHeader.vue'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'
import { focus as vFocus } from '@/directives'
import { createDialog } from '@/utils/dialogs'
import { useLocalStorage } from '@vueuse/core'
import { GPDiscussion, GPDraft } from '@/types/doctypes'

const currentRoute = useRoute()
const sessionUser = useSessionUser()
const router = useRouter()

const selectedSpace = ref<{ label: string; value: string } | null>(null)
const textEditorRef = useTemplateRef('textEditorRef')
const discussions = useDoctype<GPDiscussion>('GP Discussion')
const errorMessage = ref<string | null>(null)
const publishing = ref(false)

const savingDraft = ref(false)
const draftId = currentRoute.query.draft as string

const draftDiscussion = useLocalStorage(
  draftId ? `draft_discussion_${draftId}` : 'new_discussion',
  {
    title: '',
    content: '',
  },
  { deep: true },
)

let draftDoc: ReturnType<typeof useDoc<GPDraft>> | null = null
if (draftId) {
  draftDoc = useDoc<GPDraft>({
    doctype: 'GP Draft',
    name: draftId,
  })
}

const spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

onMounted(() => {
  if (currentRoute.query?.spaceId) {
    selectSpaceById(currentRoute.query.spaceId as string)
  }

  // if draft is present, load it
  if (draftDoc) {
    draftDoc.onSuccess((doc) => {
      draftDiscussion.value.title = doc.title || ''
      draftDiscussion.value.content = doc.content || ''
      if (doc.project) {
        selectSpaceById(doc.project)
      }
    })
  } else {
    // Clear localStorage values when starting a new discussion
    draftDiscussion.value.title = ''
    draftDiscussion.value.content = ''
    selectedSpace.value = null
  }
})

function selectSpaceById(spaceId: string) {
  let spaceOption = spaceOptions.value
    .map((group) => group.items)
    .flat()
    .find((space) => space.value.toString() === spaceId)
  if (spaceOption) {
    selectedSpace.value = spaceOption
  }
}

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
  publishing.value = true

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
      if (draftDoc?.doc) {
        draftDoc.delete.submit()
      }
    })
    .catch(() => {
      publishing.value = false
    })
}

function resetValues() {
  selectedSpace.value = null
  draftDiscussion.value.title = ''
  draftDiscussion.value.content = ''
  publishing.value = false
}

function saveDraft() {
  if (!draftDiscussion.value.title || !draftDiscussion.value.content) {
    errorMessage.value = 'Please enter title and content before saving draft.'
    return
  }
  savingDraft.value = true
  let draft = useNewDoc<GPDraft>('GP Draft', {
    title: draftDiscussion.value.title,
    content: draftDiscussion.value.content,
    project: selectedSpace.value?.value,
    type: 'Discussion',
  })
  draft
    .submit()
    .then((doc) => {
      // Save current content to the new draft's localStorage key
      const newStorageKey = `draft_discussion_${doc.name}`
      localStorage.setItem(
        newStorageKey,
        JSON.stringify({
          title: draftDiscussion.value.title,
          content: draftDiscussion.value.content,
        }),
      )

      router.replace({ name: 'NewDiscussion', query: { draft: doc.name } })
      draftDoc = useDoc<GPDraft>({
        doctype: 'GP Draft',
        name: doc.name,
      })
    })
    .finally(() => (savingDraft.value = false))
}

const updateDraftDebounced = debounce(updateDraft, 500)

function updateDraft() {
  if (!draftDiscussion.value.title || !draftDiscussion.value.content) {
    return
  }
  if (
    draftDoc?.doc &&
    (draftDoc.doc.title !== draftDiscussion.value.title ||
      draftDoc.doc.content !== draftDiscussion.value.content ||
      draftDoc.doc.project !== selectedSpace.value?.value)
  ) {
    savingDraft.value = true
    draftDoc.setValue
      .submit({
        title: draftDiscussion.value.title,
        content: draftDiscussion.value.content,
        project: selectedSpace.value?.value,
      })
      .finally(() => (savingDraft.value = false))
  }
}

function deleteDraft() {
  createDialog({
    title: 'Delete draft',
    message: 'Are you sure you want to delete this draft?',
    actions: [
      {
        label: 'Delete draft',
        onClick: ({ close }) => {
          return draftDoc?.delete.submit().then(() => {
            resetValues()
            close()
            router.back()
          })
        },
        variant: 'solid',
      },
    ],
  })
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
