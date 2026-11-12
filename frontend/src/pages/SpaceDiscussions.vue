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
      <template v-if="canStartDiscussion && !isBulkMoveMode">
        <Button
          variant="solid"
          icon-left="lucide-plus"
          label="New discussion"
          :route="{
            name: 'NewDiscussion',
            params: { communityId: route.params.communityId },
            query: { spaceId },
          }"
        />
      </template>
      <template v-else-if="isBulkMoveMode">
        <Button variant="ghost" @click="cancelBulkMove">Cancel</Button>
        <Button
          variant="solid"
          icon-left="lucide-folder-input"
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
    <DiscussionFeedBar v-model="feedType" :counts="{ unread: getSpaceUnreadCount(spaceId) }" />
    <DiscussionList
      class="-mx-3"
      ref="discussionListRef"
      :key="feedType"
      :filters="() => ({ project: spaceId, feed_type: feedType })"
      :orderBy="() => discussionOrderBy"
      :cacheKey="`SpaceDiscussions-${spaceId}-${feedType}`"
      :selectable="isBulkMoveMode"
      :empty-state="feedEmptyStates[feedType]"
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
      <ErrorMessage
        class="mt-2"
        :message="
          bulkMoveDiscussions.error
            ? errorText(bulkMoveDiscussions.error, 'Could not move the discussions.')
            : undefined
        "
      />
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
import { Button, Combobox, Dialog, ErrorMessage, useCall, toast } from 'frappe-ui'
import DiscussionFeedBar from '@/components/DiscussionFeedBar.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import SpaceAccessDialog from '@/components/SpaceAccessDialog.vue'
import PushPin from '@/components/icons/PushPin.vue'
import PushPinSlash from '@/components/icons/PushPinSlash.vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { isSpacePinned, toggleSpacePinned } from '@/data/pinnedSpaces'
import { useCommunity } from '@/data/communities'
import { discussionOrderBy } from '@/data/discussionSort'
import { feedEmptyStates, type FeedType } from '@/data/discussionFeeds'
import { useSessionUser } from '@/data/users'
import { canManageCommunity } from '@/utils/permissions'
import { showCommunitiesSettings } from '@/components/Settings'
import {
  useSpace,
  useSpacePermissions,
  canPostInSpace,
  spaces,
  getSpaceUnreadCount,
  markAllAsRead,
  archiveSpace,
  unarchiveSpace,
} from '@/data/spaces'
import { copyToClipboard, errorText } from '@/utils'
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
  feedType?: FeedType
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
  canEditSettings,
  canManageAccess,
  canMoveDiscussions,
} = useSpacePermissions(() => props.spaceId)
// Not `canEditSettings`: that one is about administering the space, and posting is open
// to every member of a live space — but not to a guest, who cannot start a discussion.
const canStartDiscussion = computed(() => canPostInSpace(currentSpace.value))
const showSpaceAccessDialog = ref(false)

// The space's community, so the "Settings" shortcut can jump to its Spaces admin
// and be gated by community-manage permission (mirrors "Manage spaces" elsewhere).
const sessionUser = useSessionUser()
const community = useCommunity(() => currentSpace.value?.team)
const canManageCurrentCommunity = computed(() => canManageCommunity(community.value, sessionUser))

// The space's feed lives in the path, as on the community feed, so a tab survives a reload
// and Back. The router only lets a known feed type through.
const feedType = computed<FeedType>({
  get: () => props.feedType ?? 'recent',
  set(feed) {
    if (feed !== feedType.value) router.push(feedRoute(feed))
  },
})

function feedRoute(feedType: FeedType) {
  const params = { communityId: route.params.communityId, spaceId: props.spaceId }
  if (feedType === 'recent') return { name: 'SpaceDiscussions', params }
  return { name: 'SpaceDiscussionsTab', params: { ...params, feedType } }
}

// Grouped as everyday actions, managing the space, then archiving.
const spaceActions = computed(() => [
  {
    group: 'Space',
    hideLabel: true,
    options: [
      {
        label: isSpacePinned(props.spaceId) ? 'Unpin space' : 'Pin space',
        icon: isSpacePinned(props.spaceId) ? PushPinSlash : PushPin,
        onClick: () => toggleSpacePinned(props.spaceId),
      },
      {
        label: 'Copy link',
        icon: 'lucide-link',
        onClick: () => copyToClipboard(window.location.href),
      },
      {
        label: 'Mark all as read…',
        icon: 'lucide-check',
        onClick: () =>
          currentSpace.value && markAllAsRead([props.spaceId], currentSpace.value.title),
      },
    ],
  },
  {
    group: 'Manage',
    hideLabel: true,
    options: [
      {
        label: 'Settings…',
        icon: 'lucide-settings',
        onClick: () => showCommunitiesSettings(currentSpace.value?.team, 'spaces'),
        condition: () => canManageCurrentCommunity.value,
      },
      {
        label: 'Manage access…',
        icon: 'lucide-users',
        onClick: () => (showSpaceAccessDialog.value = true),
        condition: () => canManageAccess.value,
      },
      {
        label: 'Move discussions',
        icon: 'lucide-folder-input',
        onClick: () => (isBulkMoveMode.value = true),
        condition: () => canMoveDiscussions.value,
      },
    ],
  },
  {
    group: 'Archive',
    hideLabel: true,
    options: [
      {
        label: 'Archive…',
        icon: 'lucide-archive',
        onClick: () =>
          currentSpace.value && archiveSpace(currentSpace.value, { fromSpacePage: true }),
        condition: () => canEditSettings.value,
      },
      {
        label: 'Unarchive',
        icon: 'lucide-archive-restore',
        onClick: () => currentSpace.value && unarchiveSpace(currentSpace.value),
        condition: () => !readOnlyMode && isArchived.value && canManageAccess.value,
      },
    ],
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
    .catch((error: unknown) => {
      toast.error(errorText(error, 'Could not move the discussions.'))
    })
}
</script>
