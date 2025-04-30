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
        <span class="mr-2 text-base text-ink-gray-9">
          <UserProfileLink class="font-medium hover:text-ink-gray-8" :user="author.name">
            {{ author.full_name }}
          </UserProfileLink>
          in
        </span>
        <Combobox
          :options="spaceOptions.map((d) => ({ group: d.group, options: d.items }))"
          v-model="draftDiscussion.project"
          placeholder="Select Space"
          :class="[author.name !== sessionUser.name ? 'pointer-events-none' : '']"
        />
      </div>
    </div>
    <ErrorMessage :message="errorMessage || discussions.insert.error || draftDoc?.publish.error" />
    <textarea
      class="mt-1 w-full bg-transparent resize-none border-0 px-0 py-0.5 text-2xl text-ink-gray-8 font-semibold placeholder-ink-gray-3 focus:ring-0"
      :value="draftDiscussion.title"
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
          const target = e.target as HTMLTextAreaElement
          draftDiscussion.title = target.value
          target.style.height = target.scrollHeight + 'px'
        }
      "
    ></textarea>
    <TextEditor
      ref="textEditorRef"
      class="mt-1 pb-40"
      editor-class="rounded-b-lg max-w-[unset] min-h-[calc(100vh-350px)] prose-sm overflow-auto"
      :content="draftDiscussion.content"
      @change="
        (content: string) => {
          draftDiscussion.content = content
        }
      "
      :editable="author.name === sessionUser.name"
      placeholder="Type '/' for commands or select text to format"
      :bubbleMenu="true"
    >
    </TextEditor>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef, onUnmounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { Breadcrumbs, Tooltip, Combobox } from 'frappe-ui'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useDoc, useDoctype, useNewDoc } from 'frappe-ui/src/data-fetching'
import { useSessionUser, useUser } from '@/data/users'
import PageHeader from '@/components/PageHeader.vue'
import TextEditor from '@/components/TextEditor.vue'
import UserProfileLink from '@/components/UserProfileLink.vue'
import { vFocus } from '@/directives'
import { createDialog } from '@/utils/dialogs'
import { useLocalStorage } from '@vueuse/core'
import { GPDiscussion, GPDraft } from '@/types/doctypes'

const currentRoute = useRoute()
const sessionUser = useSessionUser()
const router = useRouter()

const textEditorRef = useTemplateRef('textEditorRef')
const discussions = useDoctype<GPDiscussion>('GP Discussion')
const errorMessage = ref<string | null>(null)
const publishing = ref(false)

const savingDraft = ref(false)
let draftId = currentRoute.query.draft as string

const getStorageKey = () => (draftId ? `draft_discussion_${draftId}` : 'new_discussion')

const draftDiscussion = useLocalStorage(
  getStorageKey(),
  {
    title: '',
    content: '',
    project: null as string | null,
  },
  { deep: true },
)

// Computed property to check if there are unsaved changes
const isDraftChanged = computed(() => {
  const currentTitle = draftDiscussion.value.title
  const currentContent = draftDiscussion.value.content
  const currentProject = draftDiscussion.value.project

  if (draftDoc.value?.doc) {
    let project = draftDoc.value.doc.project?.toString() || null
    return (
      currentTitle !== (draftDoc.value.doc.title || '') ||
      currentContent !== (draftDoc.value.doc.content || '') ||
      currentProject !== project
    )
  } else {
    return !!(currentTitle || currentContent || currentProject)
  }
})

interface DraftMethods {
  publish: () => string
}

let draftDoc = ref<ReturnType<typeof useDoc<GPDraft, DraftMethods>> | null>(null)
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
  if (draftDoc.value) {
    draftDoc.value.onSuccess((doc) => {
      if (draftDoc.value?.doc?.name === doc.name) {
        draftDiscussion.value.title = doc.title || ''
        draftDiscussion.value.content = doc.content || ''
        draftDiscussion.value.project = doc.project || null
      }
    })
  } else {
    draftDiscussion.value.title = ''
    draftDiscussion.value.content = ''
    draftDiscussion.value.project = (currentRoute.query.spaceId as string) || null
  }

  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

const handleBeforeUnload = (event: BeforeUnloadEvent) => {
  if (isDraftChanged.value) {
    event.preventDefault()
  }
}

onBeforeRouteLeave((to, from, next) => {
  if (isDraftChanged.value) {
    createDialog({
      title: 'Unsaved Changes',
      message: 'You have unsaved changes. Do you want to save them before leaving?',
      actions: [
        {
          label: 'Discard',
          variant: 'subtle',
          onClick: ({ close }) => {
            resetValues()
            close()
            next()
          },
        },
        {
          label: 'Save Draft',
          variant: 'solid',
          onClick: async ({ close }) => {
            try {
              await saveDraft()
              close()
              next()
            } catch (e) {
              console.error('Failed to save draft before leaving:', e)
            }
          },
        },
      ],
    })
  } else {
    next()
  }
})

function fetchDraftDoc(draftId: string) {
  draftDoc.value = useDoc<GPDraft, DraftMethods>({
    doctype: 'GP Draft',
    name: draftId,
    methods: {
      publish: 'publish',
    },
  })
  return draftDoc.value.onSuccess(() => updateLocalDraft())
}

function updateLocalDraft() {
  if (!draftDoc.value?.doc) return
  let doc = draftDoc.value.doc
  draftDiscussion.value.title = doc.title || ''
  draftDiscussion.value.content = doc.content || ''
  draftDiscussion.value.project = doc.project ? doc.project.toString() : null
}

function validateDraft(checkProject = true): boolean {
  errorMessage.value = null // Reset error message first
  if (!draftDiscussion.value.title) {
    errorMessage.value = 'Please enter title.'
    return false
  }
  if (checkProject && !draftDiscussion.value.project) {
    errorMessage.value = 'Please select a space.'
    return false
  }
  return true
}

function publish() {
  if (!validateDraft(true)) {
    return
  }
  publishing.value = true

  if (draftDoc.value?.doc) {
    return draftDoc.value.setValue
      .submit({
        title: draftDiscussion.value.title,
        content: draftDiscussion.value.content,
        project: draftDiscussion.value.project,
      })
      .then(() => draftDoc.value?.publish.submit())
      .then((discussionId) => {
        router.replace({
          name: 'Discussion',
          params: {
            spaceId: draftDiscussion.value.project,
            postId: discussionId,
          },
        })
        resetValues()
      })
      .catch(() => {
        publishing.value = false
      })
  }

  return discussions.insert
    .submit({
      title: draftDiscussion.value.title,
      content: draftDiscussion.value.content,
      project: draftDiscussion.value.project,
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
  draftDiscussion.value.project = null
  draftDiscussion.value.title = ''
  draftDiscussion.value.content = ''
  publishing.value = false
  localStorage.removeItem(getStorageKey())
}

async function executeWithMinDuration(asyncFn: () => Promise<any>, minDurationMs: number = 1000) {
  const startTime = Date.now()
  try {
    const result = await asyncFn()
    const endTime = Date.now()
    const duration = endTime - startTime
    const remainingTime = minDurationMs - duration

    if (remainingTime > 0) {
      await new Promise((resolve) => setTimeout(resolve, remainingTime))
    }
    return result
  } catch (error) {
    const endTime = Date.now()
    const duration = endTime - startTime
    const remainingTime = minDurationMs - duration
    if (remainingTime > 0) {
      await new Promise((resolve) => setTimeout(resolve, remainingTime))
    }
    throw error
  }
}

async function _updateDraft() {
  if (!draftDoc.value?.doc) return

  await draftDoc.value.setValue.submit({
    title: draftDiscussion.value.title,
    content: draftDiscussion.value.content,
    project: draftDiscussion.value.project,
  })
}

async function _createDraft() {
  let draft = useNewDoc<GPDraft>('GP Draft', {
    title: draftDiscussion.value.title,
    content: draftDiscussion.value.content,
    project: draftDiscussion.value.project,
    type: 'Discussion',
  })

  const doc = await draft.submit()

  router.replace({ name: 'NewDiscussion', query: { draft: doc.name } })
  draftId = doc.name
  fetchDraftDoc(doc.name)
}

async function saveDraft() {
  if (!validateDraft(false)) {
    return
  }

  savingDraft.value = true
  errorMessage.value = null

  try {
    await executeWithMinDuration(async () => {
      if (draftDoc.value?.doc) {
        await _updateDraft()
      } else {
        await _createDraft()
      }
    })
  } catch (error) {
    console.error('Error saving draft:', error)
    errorMessage.value = 'Failed to save draft.'
  } finally {
    savingDraft.value = false
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
          return draftDoc.value?.delete.submit().then(() => {
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
  return useUser(draftDoc.value ? draftDoc.value.doc?.owner : sessionUser.name)
})
</script>
