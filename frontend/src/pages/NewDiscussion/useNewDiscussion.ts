import { ref, computed, onMounted, provide, inject, watch, type InjectionKey } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { call, useDoctype, dialog } from 'frappe-ui'
import { useDraftSync, type DraftPayload } from '@/data/useDraftSync'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { getSpace } from '@/data/spaces'
import { useSessionUser, useUser } from '@/data/users'
import { tags } from '@/data/tags'
import type { GPDiscussion } from '@/types/doctypes'

const PUBLISH_DRAFT = 'gameplan.gameplan.doctype.gp_draft.gp_draft.publish_draft'
const LOADING_STATUS_DELAY_MS = 200

/** Title or non-empty body — the threshold for persisting a draft at all. */
function hasMeaningfulContent(payload: Partial<DraftPayload>): boolean {
  const body = (payload.content ?? '').trim()
  const title = (payload.title ?? '').trim()
  return title.length > 0 || (body.length > 0 && body !== '<p></p>')
}

export function useNewDiscussion() {
  const route = useRoute()
  const router = useRouter()
  const sessionUser = useSessionUser()
  const discussions = useDoctype<GPDiscussion>('GP Discussion')

  // The canonical composer route carries the community; the legacy route does not.
  const communityId = computed(() => optionalParam(route.params.communityId))
  const isScoped = computed(() => Boolean(communityId.value))

  const errorMessage = ref<string | null>(null)
  const publishError = ref<string | null>(null)
  const publishing = ref(false)
  const isPublishingSuccessfully = ref(false)
  const isDeletingDraft = ref(false)
  const hasInteracted = ref(false)

  // Bound to the URL so a reload — or a draft opened from the Drafts list — resumes the
  // same row. The composable assigns this (via onCreate) the moment it creates the draft,
  // which is what keeps two new-discussion tabs from sharing one row.
  const draftName = computed(() => (route.query.draft as string) || null)

  const draft = useDraftSync({
    identity: { type: 'Discussion', mode: 'New' },
    draftName,
    canSave: hasMeaningfulContent,
    initialPayload: () => ({
      title: '',
      content: '',
      project: (route.query.spaceId as string) || null,
    }),
    onCreate: (name) => syncDraftToRoute(name),
  })

  const draftData = draft.data
  const isPersisted = computed(() => Boolean(draft.serverName.value))

  // Drafts are owner-scoped on the server, so the author is always the current user.
  const author = computed(() => useUser(sessionUser.name))
  const isDraftLoading = computed(() => !draft.ready.value)
  const isComposerEditable = computed(
    () => author.value.name === sessionUser.name && !isDraftLoading.value,
  )
  const showDraftLoadingStatus = ref(false)

  // Keep fast IndexedDB/server restores visually quiet, but expose a real status when a
  // request is slow enough that the temporarily disabled composer needs explanation.
  watch(
    isDraftLoading,
    (loading, _wasLoading, onCleanup) => {
      showDraftLoadingStatus.value = false
      if (!loading) return

      const timer = window.setTimeout(() => {
        showDraftLoadingStatus.value = isDraftLoading.value
      }, LOADING_STATUS_DELAY_MS)
      onCleanup(() => window.clearTimeout(timer))
    },
    { immediate: true },
  )

  // In scoped mode the picker only offers spaces from the route's community; the
  // legacy route keeps the full grouped list.
  const spaceOptions = useGroupedSpaceOptions({
    filterFn: (space) =>
      !space.archived_at && (!isScoped.value || space.team === communityId.value),
  })

  const immediateSave = () => draft.flush()

  function syncDraftToRoute(name: string) {
    if (communityId.value) {
      router.replace({
        name: 'NewDiscussion',
        params: { communityId: communityId.value },
        query: draftRouteQuery(name, draftData.value.project),
      })
    } else {
      router.replace({
        name: 'LegacyNewDiscussion',
        query: draftRouteQuery(name, draftData.value.project),
      })
    }
  }

  // A draft opened on the legacy route that already belongs to a space is moved onto the
  // canonical scoped route. Drafts with no resolvable community stay on the legacy route.
  function normalizeDraftRoute() {
    if (isScoped.value) return false
    const project = draftData.value.project
    if (!project) return false
    const targetCommunityId = getSpace(project)?.team
    if (!targetCommunityId) return false
    router.replace({
      name: 'NewDiscussion',
      params: { communityId: targetCommunityId },
      query: draftRouteQuery(draft.serverName.value || draftName.value, project),
    })
    return true
  }

  function syncSelectedSpaceToRoute(spaceId: string | null | undefined) {
    if (routeQueryString(route.query.spaceId) === (spaceId || null)) return

    const query = { ...route.query }
    if (spaceId) {
      query.spaceId = spaceId
    } else {
      delete query.spaceId
    }
    router.replace({ query })
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
    // Height autosizing is handled by useTextareaAutosize in DiscussionBody.vue.
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

  // Publish: flush the latest content, then turn the draft into a discussion. The draft
  // row is deleted server-side by publish, so we only forget the local copy afterwards.
  async function publish() {
    hasInteracted.value = true
    publishError.value = null
    if (!validateDraft(true)) return

    publishing.value = true
    try {
      await draft.flush()

      let discussionId: string | undefined
      if (draft.serverName.value) {
        isPublishingSuccessfully.value = true
        discussionId = await call(PUBLISH_DRAFT, { name: draft.serverName.value })
      } else {
        // No server row (e.g. the flush failed) — publish directly so nothing is lost.
        isPublishingSuccessfully.value = true
        const doc = await discussions.insert.submit({
          title: draftData.value.title,
          content: draftData.value.content,
          project: draftData.value.project || undefined,
        })
        discussionId = doc?.name
      }

      await draft.forget()

      if (discussionId) {
        const spaceId = draftData.value.project
        const targetCommunityId = communityId.value || (spaceId ? getSpace(spaceId)?.team : null)
        await router.replace({
          name: 'Discussion',
          params: { communityId: targetCommunityId, spaceId, postId: discussionId },
        })
        tags.reload()
      }
    } catch (error: any) {
      publishError.value = error?.message || String(error)
      publishing.value = false
    } finally {
      isPublishingSuccessfully.value = false
    }
  }

  async function deleteDraft() {
    if (!hasMeaningfulContent(draftData.value)) {
      isDeletingDraft.value = true
      await draft.clear()
      leaveDraft()
      return
    }

    dialog.danger({
      title: 'Delete this draft?',
      message: 'This will permanently delete the draft and cannot be undone.',
      confirmLabel: 'Delete draft',
      onConfirm: async () => {
        isDeletingDraft.value = true
        await draft.clear()
        leaveDraft()
      },
    })
  }

  function leaveDraft() {
    router.replace({ name: 'Drafts' })
  }

  function initialize() {
    onMounted(() => {
      // Move legacy-route drafts onto the canonical scoped route once their space is known.
      watch(
        () => draft.ready.value,
        (ready) => {
          if (!ready) return
          if (!normalizeDraftRoute()) syncSelectedSpaceToRoute(draftData.value.project)
        },
        { immediate: true },
      )
      watch(
        () => draftData.value.project,
        (spaceId) => {
          if (!draft.ready.value) return
          if (!normalizeDraftRoute()) syncSelectedSpaceToRoute(spaceId)
        },
      )
    })

    // Frictionless leave: drafts auto-save, so navigating away just flushes any pending
    // change instead of prompting. Explicit Delete still removes the draft.
    onBeforeRouteLeave(async () => {
      if (isDeletingDraft.value || isPublishingSuccessfully.value) return true
      if (draft.dirty.value) {
        try {
          await draft.flush()
        } catch (error) {
          console.error('Failed to save draft before leaving:', error)
        }
      }
      return true
    })
  }

  return {
    // Data
    draftData,
    isPersisted,
    publishError,
    errorMessage,
    sessionUser,
    author,
    spaceOptions,

    // State
    isDraftLoading,
    isComposerEditable,
    showDraftLoadingStatus,
    publishing,
    isPublishingSuccessfully,
    isDeletingDraft,

    // Actions
    publish,
    deleteDraft,
    handleTitleInput,
    handleTitleBlur,
    handleSpaceChange,

    // Lifecycle
    initialize,
  }
}

function optionalParam(value: string | string[] | undefined): string | undefined {
  const resolved = Array.isArray(value) ? value[0] : value
  return resolved || undefined
}

function routeQueryString(value: unknown): string | null {
  const resolved = Array.isArray(value) ? value[0] : value
  return typeof resolved === 'string' && resolved.length > 0 ? resolved : null
}

function draftRouteQuery(draftName: string | null | undefined, spaceId: string | null | undefined) {
  return {
    draft: draftName || undefined,
    spaceId: spaceId || undefined,
  }
}

export type NewDiscussionContext = ReturnType<typeof useNewDiscussion>
export const NewDiscussionKey: InjectionKey<NewDiscussionContext> = Symbol('NewDiscussion')

export function provideNewDiscussion() {
  const context = useNewDiscussion()
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
