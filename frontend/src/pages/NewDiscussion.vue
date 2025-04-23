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
    <div class="hidden shrink-0 space-x-2 sm:block">
      <Button v-if="draftDoc?.doc" @click="deleteDraft" :disabled="sessionUser.name != author.name">
        Delete
      </Button>
      <Button v-else @click="discard"> Discard </Button>
      <Button @click="saveDraft" :loading="savingDraft" :disabled="!isDraftChanged || savingDraft">
        Save Draft
        <template #suffix>
          <KeyboardShortcut ctrl> S </KeyboardShortcut>
        </template>
      </Button>
      <Tooltip text="You cannot publish this draft" :disabled="sessionUser.name == author.name">
        <Button
          variant="solid"
          :loading="publishing"
          @click="publish"
          :disabled="sessionUser.name != author.name"
        >
          Publish
        </Button>
      </Tooltip>
    </div>
  </PageHeader>
  <div class="mx-auto max-w-3xl px-4 xl:px-0">
    <div class="pt-14 mb-2 flex items-center space-x-3">
      <UserProfileLink :user="author.name">
        <UserAvatar size="lg" :user="author.name" />
      </UserProfileLink>
      <div class="flex w-full items-center">
        <span class="mr-2 text-base text-gray-900">
          <UserProfileLink class="font-medium hover:text-blue-600" :user="author.name">
            {{ author.full_name }}
          </UserProfileLink>
          in
        </span>
        <Combobox
          :options="spaceOptions.map((d) => ({ group: d.group, options: d.items }))"
          v-model="selectedSpace"
          placeholder="Select Space"
          :class="[author.name !== sessionUser.name ? 'pointer-events-none' : '']"
        />
      </div>
    </div>
    <ErrorMessage :message="errorMessage || discussions.insert.error || draftDoc?.publish.error" />
    <textarea
      class="mt-1 w-full resize-none border-0 px-0 py-0.5 text-2xl text-ink-gray-8 font-semibold placeholder-gray-400 focus:ring-0"
      v-model="draftDiscussion.title"
      placeholder="Title"
      rows="1"
      wrap="soft"
      maxlength="140"
      v-focus
      @keydown.enter.prevent="textEditorRef.editor.commands.focus()"
      @keydown.down.prevent="textEditorRef.editor.commands.focus()"
      :disabled="sessionUser.name != author.name"
      @input="
        (e) => {
          e.target.style.height = e.target.scrollHeight + 'px'
        }
      "
    ></textarea>
    <TextEditor
      ref="textEditorRef"
      class="mt-1 pb-40"
      editor-class="rounded-b-lg max-w-[unset] min-h-[calc(100vh-350px)] prose-sm overflow-auto"
      :content="draftDiscussion.content"
      @change="
        (content) => {
          draftDiscussion.content = content
        }
      "
      :editable="author.name === sessionUser.name"
      placeholder="Write something, '/' for commands"
    >
    </TextEditor>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Breadcrumbs, Tooltip, Combobox } from 'frappe-ui'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useDoc, useDoctype, useNewDoc } from 'frappe-ui/src/data-fetching'
import { useSessionUser, useUser } from '@/data/users'
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

const selectedSpace = ref<string | null>(null)
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

// Computed property to check if there are unsaved changes
const isDraftChanged = computed(() => {
  const currentTitle = draftDiscussion.value.title
  const currentContent = draftDiscussion.value.content
  const currentSpace = selectedSpace.value

  if (draftDoc?.doc) {
    return (
      currentTitle !== (draftDoc.doc.title || '') ||
      currentContent !== (draftDoc.doc.content || '') ||
      currentSpace !== (draftDoc.doc.project || null)
    )
  } else {
    return !!(currentTitle || currentContent || currentSpace)
  }
})

interface DraftMethods {
  publish: () => string
}

let draftDoc: ReturnType<typeof useDoc<GPDraft, DraftMethods>> | null = null
if (draftId) {
  fetchDraftDoc(draftId)
}

const spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

// Keyboard shortcut handler
const handleKeyDown = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 's') {
    event.preventDefault()
    if (isDraftChanged.value && !savingDraft.value) {
      saveDraft()
    }
  }
}

onMounted(() => {
  if (currentRoute.query?.spaceId) {
    selectSpaceById(currentRoute.query.spaceId as string)
  }

  if (draftDoc) {
    draftDoc.onSuccess((doc) => {
      draftDiscussion.value.title = doc.title || ''
      draftDiscussion.value.content = doc.content || ''
      if (doc.project) {
        selectSpaceById(doc.project)
      }
    })
  } else {
    draftDiscussion.value.title = ''
    draftDiscussion.value.content = ''
    selectedSpace.value = null
  }

  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

function fetchDraftDoc(draftId: string) {
  draftDoc = useDoc<GPDraft, DraftMethods>({
    doctype: 'GP Draft',
    name: draftId,
    methods: {
      publish: 'publish',
    },
  })
}

function selectSpaceById(spaceId: string) {
  setTimeout(() => {
    selectedSpace.value = spaceId
  }, 0)
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

  if (draftDoc?.doc) {
    return draftDoc.publish.submit().then((discussionId) => {
      router.replace({
        name: 'Discussion',
        params: {
          spaceId: selectedSpace.value,
          postId: discussionId,
        },
      })
      resetValues()
    })
  }

  return discussions.insert
    .submit({
      project: selectedSpace.value,
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
  const startTime = Date.now()
  let savePromise: Promise<any>

  if (draftDoc?.doc) {
    savePromise = draftDoc.setValue
      .submit({
        title: draftDiscussion.value.title,
        content: draftDiscussion.value.content,
        project: selectedSpace.value,
      })
      .then((doc) => {
        draftDiscussion.value.content = doc.content
      })
  } else {
    let draft = useNewDoc<GPDraft>('GP Draft', {
      title: draftDiscussion.value.title,
      content: draftDiscussion.value.content,
      project: selectedSpace.value,
      type: 'Discussion',
    })
    savePromise = draft.submit().then((doc) => {
      const newStorageKey = `draft_discussion_${doc.name}`
      localStorage.setItem(
        newStorageKey,
        JSON.stringify({
          title: draftDiscussion.value.title,
          content: draftDiscussion.value.content,
        }),
      )
      localStorage.removeItem('new_discussion')

      router.replace({ name: 'NewDiscussion', query: { draft: doc.name } })
      fetchDraftDoc(doc.name)
    })
  }

  savePromise.finally(() => {
    const endTime = Date.now()
    const duration = endTime - startTime
    const remainingTime = 1000 - duration

    if (remainingTime > 0) {
      setTimeout(() => {
        savingDraft.value = false
      }, remainingTime)
    } else {
      savingDraft.value = false
    }
  })
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

const author = computed(() => {
  return useUser(draftDoc ? draftDoc.doc?.owner : sessionUser.name)
})

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
