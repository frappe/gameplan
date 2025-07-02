import { ref, computed, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import { useDoc } from 'frappe-ui/src/data-fetching'
import type { GPDraft } from '@/types/doctypes'
import type { DraftData, DraftMethods, DraftDocument, IsDraftChangedComputed } from './types'

export function useDraftData() {
  const currentRoute = useRoute()
  const draftId = currentRoute.query.draft as string

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

  const errorMessage = ref<string | null>(null)

  const validateDraft = (checkProject = true): boolean => {
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

  const isDraftChanged: IsDraftChangedComputed = computed(() => {
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

  if (draftId) {
    fetchDraftDoc(draftId)
  }

  return {
    draftId,
    draftData,
    draftDoc,

    errorMessage,
    validateDraft,

    isDraftChanged,

    fetchDraftDoc,
    updateLocalDraft,
    resetValues,
    initializeFromRoute,
  }
}
