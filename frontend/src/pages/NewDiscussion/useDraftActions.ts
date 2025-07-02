import { ref, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNewDoc } from 'frappe-ui/src/data-fetching'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { tags } from '@/data/tags'
import { createDialog } from '@/utils/dialogs'
import type { GPDraft, GPDiscussion } from '@/types/doctypes'
import type {
  DraftData,
  DraftDocument,
  ValidateDraftFunction,
  ResetValuesFunction,
  TextEditorRef,
  FetchDraftDocFunction,
  ErrorMessage,
  PublishingRef,
  SavingDraftRef,
  IsPublishingSuccessfullyRef,
  IsDeletingDraftRef,
  SaveDraftFunction,
} from './types'

export function useDraftActions(
  draftData: Ref<DraftData>,
  draftDoc: Ref<DraftDocument>,
  validateDraft: ValidateDraftFunction,
  resetValues: ResetValuesFunction,
  fetchDraftDoc: FetchDraftDocFunction,
  errorMessage: ErrorMessage,
  textEditorRef?: TextEditorRef,
) {
  const router = useRouter()
  const discussions = useDoctype<GPDiscussion>('GP Discussion')

  const publishing: PublishingRef = ref(false)
  const savingDraft: SavingDraftRef = ref(false)
  const isPublishingSuccessfully: IsPublishingSuccessfullyRef = ref(false)
  const isDeletingDraft: IsDeletingDraftRef = ref(false)

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
      title: draftData.value.title,
      content: draftData.value.content,
      project: draftData.value.project || undefined,
    })
  }

  async function _createDraft() {
    let draft = useNewDoc<GPDraft>('GP Draft', {
      title: draftData.value.title,
      content: draftData.value.content,
      project: draftData.value.project || undefined,
      type: 'Discussion',
    })

    const doc = await draft.submit()

    router.replace({ name: 'NewDiscussion', query: { draft: doc.name } })
    fetchDraftDoc(doc.name)
  }

  const saveDraft: SaveDraftFunction = async () => {
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
              isDeletingDraft.value = true
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
    if (!textEditorRef?.value?.editor?.isEmpty || draftData.value.title) {
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

  return {
    publishing,
    savingDraft,
    isPublishingSuccessfully,
    isDeletingDraft,

    publish,
    saveDraft,
    deleteDraft,
    discard,
  }
}
