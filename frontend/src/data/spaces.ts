import { computed, MaybeRefOrGetter, ref, toValue } from 'vue'
import { useCall, useList, useDoctype, dialog, toast } from 'frappe-ui'
import { GPProject, GPMember } from '@/types/doctypes'
import { getProjectUnreadCount, markSpacesAsRead } from './unreadCount'
import { useSessionUser } from './users'
import { canManageSpace, isGuest } from '@/utils/permissions'
import { readOnlyMode } from './readOnlyMode'
import { errorText } from '@/utils'

interface Member extends Pick<GPMember, 'user'> {}

export interface Space extends Pick<
  GPProject,
  | 'name'
  | 'title'
  | 'icon'
  | 'team'
  | 'archived_at'
  | 'is_private'
  | 'modified'
  | 'tasks_count'
  | 'discussions_count'
> {
  team_title: string
  members: Member[]
}

export let spaces = useList<Space>({
  doctype: 'GP Project',
  fields: [
    'name',
    'title',
    'icon',
    'team',
    'archived_at',
    'is_private',
    'modified',
    'tasks_count',
    'discussions_count',
    'team.title as team_title',
    { members: ['user'] },
  ],
  initialData: [],
  orderBy: 'title asc',
  limit: 99999,
  cacheKey: 'spaces',
  transform(data) {
    for (let space of data) {
      space.name = space.name.toString()
    }
    return data
  },
  immediate: true,
})

/**
 * A failed request leaves the list empty, which reads the same as a community with no
 * spaces. Callers check this before saying a space is missing or that there are none.
 * Cached rows still count as loaded when only a refresh fails.
 */
export const spacesStatus = computed<'loading' | 'ready' | 'failed'>(() => {
  if (spaces.data?.length) return 'ready'
  if (spaces.error) return 'failed'
  return spaces.isFinished ? 'ready' : 'loading'
})

export function useSpace(name: MaybeRefOrGetter<string | undefined>) {
  return computed(() => {
    let _name = toValue(name)
    if (!_name) return null
    return getSpace(_name)
  })
}

/**
 * Shared gates for the space-action menus (the options dropdown and the discussions-header
 * menu). Kept in one place so a permission-rule change can't leave the two menus disagreeing
 * about who may edit vs. manage a space. `canEditSpace` only says the space is writable at all
 * (live, and not read-only mode); `canManageAccess` mirrors the backend `can_manage_space`;
 * `canEditSettings` is both, and gates everything that writes GP Project itself (rename, change
 * community, merge, archive, delete); `canMoveDiscussions` gates the bulk move, which is neither
 * an edit nor an admin action.
 *
 * The move is kept off `canEditSpace` because a guest may edit content in a space they were
 * granted, but the backend refuses a move from a guest outright.
 */
export function useSpacePermissions(spaceId: MaybeRefOrGetter<string | undefined>) {
  const space = useSpace(spaceId)
  const sessionUser = useSessionUser()
  const isArchived = computed(() => Boolean(space.value?.archived_at))
  const isGuestUser = computed(() => isGuest(sessionUser))
  const canEditSpace = computed(() => !readOnlyMode && !isArchived.value)
  const canManageAccess = computed(() => !readOnlyMode && canManageSpace(space.value, sessionUser))
  // Renaming a space, moving it, merging it, archiving or deleting it are all writes
  // on GP Project, which the backend gates with can_manage_space. canEditSpace only
  // says the space is writable at all (not archived, not read-only), so it is never
  // enough on its own — every member can read a public space they do not manage.
  const canEditSettings = computed(() => canEditSpace.value && canManageAccess.value)
  const canMoveDiscussions = computed(() => canEditSpace.value && !isGuestUser.value)
  return {
    space,
    isArchived,
    canEditSpace,
    canEditSettings,
    canManageAccess,
    canMoveDiscussions,
  }
}

/**
 * Can a new discussion be started in this space? The backend refuses posts in an archived
 * space, and read-only mode blocks every write, so both are filtered out before a space is
 * ever offered as a target.
 *
 * Membership is not part of the test, for guests or anyone else, because read access and
 * post access are the same thing. Backend `can_create_content` lets a guest start a
 * discussion in any space they can view, and a guest's spaces list holds only the spaces
 * they were granted. Pages and tasks stay closed to guests; they are gated separately.
 */
export function canPostInSpace(space: Space | null | undefined) {
  return Boolean(space && !readOnlyMode && !space.archived_at)
}

export function getSpace(name: string) {
  return spaces.data?.find((space) => space.name.toString() === name.toString()) ?? null
}

export const joinedSpaces = useCall<string[]>({
  url: '/api/v2/method/GP Project/get_joined_spaces',
  cacheKey: 'joinedSpaces',
  initialData: [],
})

export function getSpaceUnreadCount(spaceId: string) {
  return getProjectUnreadCount(spaceId)
}

export function trackSpaceVisit(spaceId: string) {
  return spaceVisitApi.runMethod.submit({
    method: 'track_visits',
    params: { spaces: [spaceId] },
  })
}

const spaceDoctype = useDoctype<GPProject>('GP Project')
// Mount-time visit tracking can overlap a menu action. Keep it off spaceDoctype's single
// shared runMethod request so the two calls cannot cross-resolve each other's state.
const spaceVisitApi = useDoctype<GPProject>('GP Project')

/**
 * The space just archived from its own page. The sidebar drops archived spaces, so it keeps
 * this one, dimmed, until the person leaves the page; otherwise the page they are on has no
 * row in the sidebar.
 */
const lingeringArchivedSpaceId = ref<string | null>(null)

export function isLingeringArchivedSpace(spaceId: string) {
  return lingeringArchivedSpaceId.value === spaceId
}

export function forgetArchivedSpace(spaceId: string) {
  if (isLingeringArchivedSpace(spaceId)) lingeringArchivedSpaceId.value = null
}

export function archiveSpace(space: Space) {
  dialog.confirm({
    title: `Archive ${space.title}?`,
    message: 'The space becomes read-only, and its discussions no longer show in feeds.',
    confirmLabel: 'Archive',
    onConfirm: async () => {
      await spaceDoctype.runDocMethod.submit({ method: 'archive', name: space.name })
      lingeringArchivedSpaceId.value = space.name
      toast.success('Space archived', {
        action: { label: 'Undo', onClick: () => undoArchiveSpace(space) },
      })
    },
  })
}

export function unarchiveSpace(space: Space) {
  return spaceDoctype.runDocMethod.submit({
    method: 'unarchive',
    name: space.name,
  })
}

export function markAllAsRead(spaceIds: string[], groupTitle: string) {
  dialog.confirm({
    title: `Mark all discussions in ${groupTitle} as read?`,
    message: 'Their unread counts will be cleared.',
    confirmLabel: 'Mark all as read',
    onConfirm: async () => {
      await markSpacesAsRead(spaceIds)
    },
  })
}

function undoArchiveSpace(space: Space) {
  unarchiveSpace(space).catch((error: unknown) =>
    toast.error(errorText(error, `Could not unarchive ${space.title}.`)),
  )
}

export function isDocMethodLoading(docname: string, method: string) {
  return spaceDoctype.runDocMethod.isLoading(docname, method)
}

export function isMethodLoading(method: string) {
  return spaceDoctype.runMethod.isLoading(method)
}
