import { computed, onMounted, provide, inject, type InjectionKey } from 'vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useSessionUser, useUser } from '@/data/users'

import { useDraftData } from './useDraftData'
import { useDraftActions } from './useDraftActions'
import { useUIBehavior } from './useUIBehavior'

import type { TextEditorRef, DraftDocumentCallback } from './types'

export function useNewDiscussion(textEditorRef?: TextEditorRef) {
  const sessionUser = useSessionUser()

  const {
    draftData,
    draftDoc,
    errorMessage,
    validateDraft,
    isDraftChanged,
    fetchDraftDoc,
    updateLocalDraft,
    resetValues,
    initializeFromRoute,
  } = useDraftData()

  const {
    publishing,
    savingDraft,
    isPublishingSuccessfully,
    isDeletingDraft,
    publish,
    saveDraft,
    deleteDraft,
    discard,
  } = useDraftActions(
    draftData,
    draftDoc,
    validateDraft,
    resetValues,
    fetchDraftDoc,
    errorMessage,
    textEditorRef,
  )

  const {
    showFixedMenu,
    handleTextareaFocus,
    handleTextareaBlur,
    handleComboboxFocus,
    handleComboboxBlur,
    setupEditorListeners,
  } = useUIBehavior(
    isDraftChanged,
    savingDraft,
    publishing,
    isPublishingSuccessfully,
    isDeletingDraft,
    saveDraft,
    resetValues,
    draftDoc,
    textEditorRef,
  )

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

  const handleTitleInput = (e: Event) => {
    const target = e.target as HTMLTextAreaElement
    draftData.value.title = target.value
    target.style.height = target.scrollHeight + 'px'
  }

  function initialize() {
    onMounted(() => {
      if (draftDoc.value) {
        draftDoc.value.onSuccess((doc: DraftDocumentCallback) => {
          if (draftDoc.value?.doc?.name === doc.name) {
            updateLocalDraft()
          }
        })
      } else {
        initializeFromRoute()
      }

      if (textEditorRef) {
        setupEditorListeners(textEditorRef)
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
    savingDraft,
    isPublishingSuccessfully,
    isDeletingDraft,
    showFixedMenu,

    // Actions
    publish,
    saveDraft,
    deleteDraft,
    discard,
    handleTitleInput,
    handleTextareaFocus,
    handleTextareaBlur,
    handleComboboxFocus,
    handleComboboxBlur,

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
