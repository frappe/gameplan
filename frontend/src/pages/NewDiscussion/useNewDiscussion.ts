import { ref, computed, onMounted, provide, inject, watch, type InjectionKey } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import { useDoc, useNewDoc, useDoctype, dialog } from 'frappe-ui'
import { debounce } from 'frappe-ui'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useSessionUser, useUser } from '@/data/users'
import { tags } from '@/data/tags'
import type { TextEditorRef, DraftDocumentCallback, DraftDocument, DraftMethods } from './types'
import type { GPDraft, GPDiscussion } from '@/types/doctypes'

export function useNewDiscussion(textEditorRef?: TextEditorRef) {
  const currentRoute = useRoute()
  const router = useRouter()
  const sessionUser = useSessionUser()
  const discussions = useDoctype<GPDiscussion>('GP Discussion')
  const draftId = currentRoute.query.draft as string

  // Core reactive state
  const getStorageKey = () => (draftId ? `draft_discussion_${draftId}` : 'new_discussion')

  const draftData = useLocalStorage(
    getStorageKey(),
    {
      title: '',
      content: '',
      project: null as string | null,
    },
    { deep: true },
  )

  const draftDoc = ref<DraftDocument>(null)
  const errorMessage = ref<string | null>(null)
  const publishing = ref(false)
  const isDeletingDraft = ref(false)
  const isPublishingSuccessfully = ref(false)
  const hasInteracted = ref(false)

  // Computed values
  const isDraftChanged = computed(() => {
    const currentTitle = draftData.value.title
    const currentContent = draftData.value.content
    const currentProject = draftData.value.project

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

  // Auto-save functionality
  const savingDraft = ref(false)

  const canAutoSave = computed(() => {
    return draftData.value.title.trim().length > 0 && !savingDraft.value
  })

  async function _updateDraft() {
    if (!draftDoc.value?.doc) return
    await draftDoc.value.setValue.submit({
      title: draftData.value.title,
      content: draftData.value.content,
      project: draftData.value.project || undefined,
    })
  }

  async function _createDraft() {
    const draft = useNewDoc<GPDraft>('GP Draft', {
      title: draftData.value.title,
      content: draftData.value.content,
      project: draftData.value.project || undefined,
      type: 'Discussion',
    })

    const doc = await draft.submit()
    router.replace({ name: 'NewDiscussion', query: { draft: doc.name } })
    fetchDraftDoc(doc.name)
  }

  async function performAutoSave() {
    if (!canAutoSave.value) return

    savingDraft.value = true
    try {
      if (draftDoc.value?.doc) {
        await _updateDraft()
      } else {
        await _createDraft()
      }
    } catch (error) {
      console.error('Auto-save failed:', error)
    } finally {
      savingDraft.value = false
    }
  }

  const debouncedAutoSave = debounce(performAutoSave, 300)
  const immediateSave = performAutoSave

  // Watch for changes and auto-save
  watch(
    () => [draftData.value.title, draftData.value.content, draftData.value.project],
    () => {
      if (canAutoSave.value) {
        debouncedAutoSave()
      }
    },
    { flush: 'post' },
  )

  const saveStatus = computed(() => ({
    isSaving: savingDraft.value,
    lastSaved: null,
    hasUnsavedChanges: isDraftChanged.value,
    error: null,
  }))

  // Space options and formatting
  const spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

  const formattedSpaceOptions = computed(() => {
    return spaceOptions.value.map((d) => {
      if ('group' in d && 'items' in d) {
        return { group: d.group, options: d.items }
      }
      return d
    })
  })

  const author = computed(() => {
    return useUser(draftDoc.value ? draftDoc.value.doc?.owner : sessionUser.name)
  })

  // Core functions
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
    const doc = draftDoc.value.doc
    draftData.value.title = doc.title || ''
    draftData.value.content = doc.content || ''
    draftData.value.project = doc.project ? doc.project.toString() : null
  }

  function resetValues() {
    draftData.value.project = null
    draftData.value.title = ''
    draftData.value.content = ''
    localStorage.removeItem(getStorageKey())
  }

  function initializeFromRoute() {
    if (!draftId) {
      draftData.value.title = ''
      draftData.value.content = ''
      draftData.value.project = (currentRoute.query.spaceId as string) || null
    }
  }

  // Validation
  const validateDraft = (checkProject = true): boolean => {
    if (!hasInteracted.value) return true // Don't validate until user has interacted

    errorMessage.value = null
    if (!draftData.value.title) {
      errorMessage.value = 'Please enter title.'
      return false
    }
    if (checkProject && !draftData.value.project) {
      errorMessage.value = 'Please select a space.'
      return false
    }
    return true
  }

  // Event handlers
  const handleTitleInput = (e: Event) => {
    const target = e.target as HTMLTextAreaElement
    draftData.value.title = target.value
    target.style.height = target.scrollHeight + 'px'
    hasInteracted.value = true
  }

  const handleTitleBlur = () => {
    hasInteracted.value = true
    immediateSave()
  }

  const handleSpaceChange = () => {
    hasInteracted.value = true
    immediateSave()
  }

  // Publish functionality
  function publish() {
    if (!validateDraft(true)) {
      return
    }
    publishing.value = true

    const projectValue = draftData.value.project || undefined

    if (draftDoc.value?.doc) {
      return draftDoc.value.setValue
        .submit({
          title: draftData.value.title,
          content: draftData.value.content,
          project: projectValue,
        })
        .then(() => {
          isPublishingSuccessfully.value = true
          return draftDoc.value?.publish.submit()
        })
        .then((discussionId: any) => {
          if (discussionId) {
            const spaceId = draftData.value.project
            resetValues()
            router
              .replace({
                name: 'Discussion',
                params: {
                  spaceId: spaceId,
                  postId: discussionId,
                },
              })
              .finally(() => {
                isPublishingSuccessfully.value = false
              })
            tags.reload()
          }
        })
        .catch(() => {
          publishing.value = false
        })
    }

    return discussions.insert
      .submit({
        title: draftData.value.title,
        content: draftData.value.content,
        project: projectValue,
      })
      .then((doc) => {
        if (doc) {
          isPublishingSuccessfully.value = true
          resetValues()
          router
            .replace({
              name: 'Discussion',
              params: {
                spaceId: doc.project,
                postId: doc.name,
              },
            })
            .finally(() => {
              isPublishingSuccessfully.value = false
            })
        }
      })
      .catch(() => {
        publishing.value = false
      })
  }

  function deleteDraft() {
    dialog.danger({
      title: 'Delete draft',
      message: 'Are you sure you want to delete this draft?',
      confirmLabel: 'Delete draft',
      onConfirm: async () => {
        await draftDoc.value?.delete.submit()
        resetValues()
        isDeletingDraft.value = true
        router.back()
      },
    })
  }

  function discard() {
    if (!textEditorRef?.value?.editor?.isEmpty || draftData.value.title) {
      dialog.danger({
        title: 'Discard post',
        message: 'Are you sure you want to discard your post?',
        confirmLabel: 'Discard post',
        onConfirm: () => {
          resetValues()
          router.back()
        },
      })
    } else {
      router.back()
    }
  }

  // Editor setup
  const setupEditorListeners = (editorRef: TextEditorRef) => {
    setTimeout(() => {
      const editor = editorRef.value?.editor
      if (editor) {
        editor.on('update', () => {
          // Trigger auto-save when editor content changes
          debouncedAutoSave()
        })
      }
    }, 100)
  }

  // Lifecycle management
  function initialize() {
    // Initialize draft document if we have a draft ID
    if (draftId) {
      fetchDraftDoc(draftId)
    } else {
      initializeFromRoute()
    }

    onMounted(() => {
      if (draftDoc.value) {
        draftDoc.value.onSuccess((doc: DraftDocumentCallback) => {
          if (draftDoc.value?.doc?.name === doc.name) {
            updateLocalDraft()
          }
        })
      }

      if (textEditorRef) {
        setupEditorListeners(textEditorRef)
      }
    })

    // Navigation guard
    onBeforeRouteLeave((_, __, next) => {
      if (isDeletingDraft.value || isPublishingSuccessfully.value || publishing.value) {
        next()
        return
      }
      if (isDraftChanged.value) {
        // Save Draft → onConfirm; Discard / Escape / outside-click → onCancel.
        dialog.confirm({
          title: 'Unsaved Changes',
          message: 'You have unsaved changes. Do you want to save them before leaving?',
          confirmLabel: 'Save Draft',
          cancelLabel: 'Discard',
          onConfirm: () => {
            try {
              immediateSave()
            } catch (e) {
              console.error('Failed to save draft before leaving:', e)
            }
            next()
          },
          onCancel: () => {
            resetValues()
            next()
          },
        })
      } else {
        next()
      }
    })
  }

  return {
    // Data
    draftData,
    draftDoc,
    errorMessage,
    sessionUser,
    author,
    formattedSpaceOptions,

    // State
    isDraftChanged,
    publishing,
    isPublishingSuccessfully,
    isDeletingDraft,
    saveStatus,

    // Actions
    publish,
    deleteDraft,
    discard,
    handleTitleInput,
    handleTitleBlur,
    handleSpaceChange,
    immediateSave,

    // Lifecycle
    initialize,
  }
}

export type NewDiscussionContext = ReturnType<typeof useNewDiscussion>
export const NewDiscussionKey: InjectionKey<NewDiscussionContext> = Symbol('NewDiscussion')

export function provideNewDiscussion(textEditorRef?: TextEditorRef) {
  const context = useNewDiscussion(textEditorRef)
  provide(NewDiscussionKey, context)
  return context
}

export function useNewDiscussionContext() {
  const context = inject(NewDiscussionKey)
  if (!context) {
    throw new Error('useNewDiscussionContext must be used within a NewDiscussion component')
  }
  return context
}
