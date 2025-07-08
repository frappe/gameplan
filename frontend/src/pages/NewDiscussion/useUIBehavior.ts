import { ref, computed, onMounted, onUnmounted, nextTick, type ComputedRef, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { debounce } from 'frappe-ui'
import { createDialog } from '@/utils/dialogs'
import type {
  SaveDraftFunction,
  ResetValuesFunction,
  TextEditorRef,
  KeyboardEventHandler,
  BeforeUnloadEventHandler,
  DraftDocument,
} from './types'

export function useUIBehavior(
  isDraftChanged: ComputedRef<boolean>,
  savingDraft: Ref<boolean>,
  publishing: Ref<boolean>,
  isPublishingSuccessfully: Ref<boolean>,
  isDeletingDraft: Ref<boolean>,
  saveDraft: SaveDraftFunction,
  resetValues: ResetValuesFunction,
  draftDoc: Ref<DraftDocument>,
  textEditorRef?: TextEditorRef,
) {
  // Editor state
  const isTextareaFocused = ref(false)
  const isComboboxFocused = ref(false)
  const hasEditorBeenFocused = ref(false)
  const hasInitialSave = ref(false)

  const showFixedMenu = computed(() => {
    return hasEditorBeenFocused.value && !isTextareaFocused.value && !isComboboxFocused.value
  })

  const canAutosave = computed(() => {
    return draftDoc.value?.doc || hasInitialSave.value
  })

  const triggerFirstSave = async () => {
    if (isDraftChanged.value && !savingDraft.value) {
      try {
        await saveDraft()
        hasInitialSave.value = true
      } catch (error) {
        console.error('First draft save failed on title blur:', error)
      }
    }
  }

  const debouncedAutosave = debounce(async () => {
    if (isDraftChanged.value && !savingDraft.value && canAutosave.value) {
      try {
        await saveDraft()
      } catch (error) {
        console.error('Autosave failed:', error)
      }
    }
  }, 1000)

  function handleTextareaFocus() {
    isTextareaFocused.value = true
    hasEditorBeenFocused.value = false
  }

  function handleTextareaBlur() {
    isTextareaFocused.value = false
    if (canAutosave.value) {
      debouncedAutosave()
    } else {
      // If we don't have an existing draft, we need to trigger the first save
      triggerFirstSave()
    }
  }

  function handleComboboxFocus() {
    isComboboxFocused.value = true
    hasEditorBeenFocused.value = false
  }

  function handleComboboxBlur() {
    isComboboxFocused.value = false
    debouncedAutosave()
  }

  function setupEditorListeners(editorRef: TextEditorRef) {
    setTimeout(() => {
      const editor = editorRef.value?.editor
      if (editor) {
        editor.on('focus', () => {
          hasEditorBeenFocused.value = true
        })

        editor.on('update', () => {
          console.log('update')
          nextTick(() => debouncedAutosave())
        })
      }
    }, 100)
  }

  // Keyboard shortcuts
  const handleKeyDown: KeyboardEventHandler = (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 's') {
      event.preventDefault()
      if (isDraftChanged.value && !savingDraft.value) {
        saveDraft()
      }
    }
  }

  // Navigation guards
  const handleBeforeUnload: BeforeUnloadEventHandler = (event: BeforeUnloadEvent) => {
    if (isDraftChanged.value) {
      event.preventDefault()
    }
  }

  // Mount/unmount lifecycle
  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('beforeunload', handleBeforeUnload)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('beforeunload', handleBeforeUnload)

    // Clean up editor listeners
    if (textEditorRef?.value?.editor) {
      textEditorRef.value.editor.off('focus')
      textEditorRef.value.editor.off('update')
    }
  })

  // Route leave guard
  onBeforeRouteLeave((to, from, next) => {
    if (isDeletingDraft.value || isPublishingSuccessfully.value || publishing.value) {
      next()
      return
    }
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

  return {
    // Editor state
    showFixedMenu,
    handleTextareaFocus,
    handleTextareaBlur,
    handleComboboxFocus,
    handleComboboxBlur,
    setupEditorListeners,
  }
}
