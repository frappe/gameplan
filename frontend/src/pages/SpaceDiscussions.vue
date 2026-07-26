<template>
  <div class="body-container mt-5">
    <SpaceHeaderActions placement="title">
      <DropdownMoreOptions
        v-if="!isBulkMoveMode"
        label="Space actions"
        align="start"
        :options="spaceActions"
      />
    </SpaceHeaderActions>
    <SpaceHeaderActions>
      <template v-if="canEditSpace && !isBulkMoveMode">
        <Button
          variant="solid"
          icon-left="lucide-plus"
          @click="
            router.push({
              name: 'NewDiscussion',
              params: { communityId: route.params.communityId },
              query: { spaceId: spaceId },
            })
          "
        >
          Add new
        </Button>
      </template>
      <template v-else-if="isBulkMoveMode">
        <Button variant="ghost" @click="cancelBulkMove">Cancel</Button>
        <Button
          variant="solid"
          icon-left="lucide-log-out"
          @click="showMoveDialog = true"
          :disabled="selectedDiscussions.length === 0"
        >
          <template v-if="selectedDiscussions.length === 0">Move discussions</template>
          <template v-else>
            Move {{ selectedDiscussions.length }} discussion{{
              selectedDiscussions.length > 1 ? 's' : ''
            }}
          </template>
        </Button>
      </template>
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>
    <DiscussionList
      class="-mx-3"
      ref="discussionListRef"
      :filters="() => ({ project: spaceId })"
      :cacheKey="`SpaceDiscussions-${spaceId}`"
      :selectable="isBulkMoveMode"
      v-model:selectedDiscussions="selectedDiscussions"
    />
    <Dialog
      title="Move discussions to another space"
      @close="resetMoveDialog"
      v-model:open="showMoveDialog"
    >
      <Combobox
        :options="spaceOptions"
        v-model="selectedSpace"
        placeholder="Select a space"
        class="w-full"
        open-on-click
        autofocus
      />
      <ErrorMessage class="mt-2" :message="bulkMoveDiscussions.error" />
      <template #actions>
        <Button
          class="w-full"
          variant="solid"
          :loading="bulkMoveDiscussions.loading"
          :disabled="!selectedSpace"
          @click="moveDiscussions"
        >
          {{ selectedSpace ? `Move to ${selectedSpaceTitle}` : 'Move' }}
        </Button>
      </template>
    </Dialog>
    <SpaceAccessDialog v-model="showSpaceAccessDialog" :spaceId="spaceId" />
  </div>
</template>
<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Combobox, Dialog, ErrorMessage, useCall, toast } from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import SpaceAccessDialog from '@/components/SpaceAccessDialog.vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useCommunity } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canManageCommunity } from '@/utils/permissions'
import { showCommunitiesSettings } from '@/components/Settings'
import {
  useSpace,
  useSpacePermissions,
  useSpaceFollowing,
  spaces,
  hasJoined,
  joinSpaces,
  leaveSpaces,
  markAllAsRead,
  archiveSpace,
  unarchiveSpace,
} from '@/data/spaces'
import { copyToClipboard } from '@/utils'
import { readOnlyMode } from '@/data/readOnlyMode'

interface BulkUpdateResponse {
  moved: string[]
  failed: { name: string; error: string }[]
  total: number
  success_count: number
  failure_count: number
}

const props = defineProps<{
  spaceId: string
}>()

const route = useRoute()
const isBulkMoveMode = ref(false)
const selectedDiscussions = ref<string[]>([])
const showMoveDialog = ref(false)
const selectedSpace = ref<string | null>(null)
const discussionListRef = useTemplateRef('discussionListRef')
const router = useRouter()
const {
  space: currentSpace,
  isArchived,
  canEditSpace,
  canManageAccess,
} = useSpacePermissions(() => props.spaceId)
const following = useSpaceFollowing(() => props.spaceId)
const isJoined = computed(() => hasJoined(props.spaceId))
const showSpaceAccessDialog = ref(false)

// The space's community, so the "Settings" shortcut can jump to its Spaces admin
// and be gated by community-manage permission (mirrors "Manage spaces" elsewhere).
const sessionUser = useSessionUser()
const community = useCommunity(() => currentSpace.value?.team)
const canManageCurrentCommunity = computed(() => canManageCommunity(community.value, sessionUser))

const spaceActions = computed(() => [
  {
    label: 'Settings',
    icon: 'lucide-settings',
    onClick: () => showCommunitiesSettings(currentSpace.value?.team, 'spaces'),
    condition: () => canManageCurrentCommunity.value,
  },
  {
    label: 'Copy link',
    icon: 'lucide-link',
    onClick: () => copyToClipboard(window.location.href),
  },
  {
    label: 'Mark all as read',
    icon: 'lucide-check',
    onClick: () => currentSpace.value && markAllAsRead([props.spaceId], currentSpace.value.title),
  },
  {
    label: isJoined.value ? 'Leave space' : 'Join space',
    icon: isJoined.value ? 'lucide-log-out' : 'lucide-log-in',
    onClick: () => {
      if (!currentSpace.value) return
      return isJoined.value ? leaveSpaces([props.spaceId]) : joinSpaces([props.spaceId])
    },
    condition: () => canEditSpace.value,
  },
  {
    label: following.isFollowed.value ? 'Unfollow space' : 'Follow space',
    icon: following.isFollowed.value ? 'lucide-bell-off' : 'lucide-bell-plus',
    onClick: () => (following.isFollowed.value ? following.unfollow() : following.follow()),
    condition: () => canEditSpace.value,
  },
  {
    label: 'Manage access',
    icon: 'lucide-users',
    onClick: () => (showSpaceAccessDialog.value = true),
    condition: () => canManageAccess.value,
  },
  {
    label: 'Move discussions',
    icon: 'lucide-log-out',
    onClick: () => (isBulkMoveMode.value = true),
    condition: () => canEditSpace.value,
  },
  {
    label: 'Archive',
    icon: 'lucide-archive',
    onClick: () => currentSpace.value && archiveSpace(currentSpace.value),
    // Archiving is destructive — gate it behind manage access, mirroring Unarchive, so a
    // regular member isn't offered (and can't submit) an action they lack permission for.
    condition: () => canEditSpace.value && canManageAccess.value,
  },
  {
    label: 'Unarchive',
    icon: 'lucide-archive-restore',
    onClick: () => currentSpace.value && unarchiveSpace(currentSpace.value),
    condition: () => !readOnlyMode && isArchived.value && canManageAccess.value,
  },
])
const selectedSpaceTitle = computed(() => {
  return selectedSpace.value ? useSpace(selectedSpace.value).value?.title : ''
})

const spaceOptions = useGroupedSpaceOptions({
  filterFn: (space) => !space.archived_at && space.name !== props.spaceId,
})

const bulkMoveDiscussions = useCall<
  BulkUpdateResponse,
  { discussions: { name: string; project: string }[] }
>({
  url: '/api/v2/method/GP Discussion/move_discussions',
  method: 'POST',
  immediate: false,
})

function cancelBulkMove() {
  isBulkMoveMode.value = false
  selectedDiscussions.value = []
}

function resetMoveDialog() {
  selectedSpace.value = null
}

function moveDiscussions() {
  if (selectedDiscussions.value.length === 0) {
    toast.error('Select discussions to move')
    return
  }
  if (!selectedSpace.value) {
    toast.error('Select a space to move discussions')
    return
  }

  bulkMoveDiscussions
    .submit({
      discussions: selectedDiscussions.value.map((name) => ({
        name,
        project: selectedSpace.value as string,
      })),
    })
    .then(() => {
      const response = bulkMoveDiscussions.data
      const successCount = response?.success_count || 0
      const failureCount = response?.failure_count || 0

      if (successCount > 0) {
        toast.success(successCount === 1 ? 'Discussion moved' : `${successCount} discussions moved`)
      }

      if (failureCount > 0) {
        selectedDiscussions.value = response?.failed.map((item) => item.name) || []
        toast.error(
          failureCount === 1
            ? '1 discussion could not be moved'
            : `${failureCount} discussions could not be moved`,
        )
        resetMoveDialog()
        showMoveDialog.value = false
        return
      }

      spaces.reload()
      if (discussionListRef.value) {
        discussionListRef.value.discussions?.reload()
        discussionListRef.value.pinnedDiscussions?.reload()
      }
      resetMoveDialog()
      selectedDiscussions.value = []
      showMoveDialog.value = false
      isBulkMoveMode.value = false
    })
    .catch(() => {
      toast.error(bulkMoveDiscussions.error || 'Failed to move discussions')
    })
}
</script>
