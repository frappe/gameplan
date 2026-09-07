<template>
  <Dropdown :options="actionOptions" match-trigger-width>
    <template #default="{ open }">
      <button
        type="button"
        class="flex w-full min-w-0 items-center justify-between rounded-4 px-2 py-1 text-ink-gray-7 transition"
        :class="open ? 'bg-surface-elevation-2 shadow-sm' : 'hover:bg-surface-gray-2'"
        :title="community?.title"
      >
        <span class="truncate text-lg-medium">{{ community?.title || 'Community' }}</span>
        <div class="grid size-7 place-content-center">
          <span class="lucide-chevron-down size-4 shrink-0 text-ink-gray-5" />
        </div>
      </button>
    </template>
  </Dropdown>

  <Dialog v-model:open="showMarkAllAsReadDialog" title="Mark all as read" :icon="dangerIcon">
    <div class="space-y-3">
      <p class="text-p-base text-ink-gray-7">
        This marks every discussion in {{ communityName }} as read, across all of its spaces, up to
        and including {{ formattedMarkReadDate }}. You cannot undo this.
      </p>
      <DatePicker
        v-model="markReadBeforeDate"
        :clearable="false"
        :max="today"
        placeholder="Select date"
        format="D MMM, YYYY"
      />
    </div>
    <template #actions>
      <!-- Cancel sits first in the DOM so the destructive button is never the one the dialog
           focuses on open, while the visual order stays cancel-left, confirm-right. -->
      <div class="flex justify-end gap-2">
        <Button
          variant="outline"
          :disabled="markingAllAsRead"
          @click="showMarkAllAsReadDialog = false"
        >
          Cancel
        </Button>
        <Button variant="solid" theme="red" :loading="markingAllAsRead" @click="markAllAsRead">
          Mark all as read
        </Button>
      </div>
    </template>
  </Dialog>

  <MergeCommunityDialog
    v-if="community"
    v-model="showMergeDialog"
    :community="community"
    @merged="goToCommunity"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, DatePicker, dayjsLocal, Dialog, dialog, Dropdown, useDoctype } from 'frappe-ui'
import type { DropdownOptions } from 'frappe-ui'
import { activeCommunities, communities } from '@/data/communities'
import { communityState } from '@/data/communityState'
import { reloadDiscussionLists } from '@/data/discussions'
import { spaceSortMenuOptions } from '@/data/sidebarPreferences'
import { useSessionUser } from '@/data/users'
import { markCommunityAsRead } from '@/data/unreadCount'
import type { GPTeam } from '@/types/doctypes'
import { copyToClipboard } from '@/utils'
import { canManageCommunity } from '@/utils/permissions'
import { showCommunitiesSettings } from '@/components/Settings'
import { useCommandPaletteCommands } from '@/components/CommandPalette/registry'
import MergeCommunityDialog from '@/pages/Configure/MergeCommunityDialog.vue'

const emit = defineEmits<{
  (event: 'new-space'): void
}>()

const router = useRouter()
const sessionUser = useSessionUser()
const teams = useDoctype<GPTeam>('GP Team')

const community = computed(() => communityState.doc)
const communityId = computed(() => communityState.id)

const markingAllAsRead = ref(false)
const showMarkAllAsReadDialog = ref(false)
const showMergeDialog = ref(false)
// Today is the latest allowed cutoff: a future date can't mark not-yet-posted discussions
// read, and the backend clamps to it anyway. Defaults to today so the action clears
// everything unless an earlier date is picked. Held in a ref and refreshed whenever the
// dialog opens so a page left open past midnight still offers the real current day.
const today = ref(dayjsLocal().format('YYYY-MM-DD'))
const markReadBeforeDate = ref(today.value)

// Matches what `dialog.danger` renders, so this hand-rolled dialog reads as the same
// kind of action as the rest of the destructive confirms.
const dangerIcon = { name: 'lucide-alert-triangle', theme: 'red' } as const

const communityName = computed(() => community.value?.title || 'this community')
// Same format as the DatePicker below, so the sentence and the field agree.
const formattedMarkReadDate = computed(() =>
  dayjsLocal(markReadBeforeDate.value).format('D MMM, YYYY'),
)

const canManageCurrentCommunity = computed(() => canManageCommunity(community.value, sessionUser))
const canCreateSpace = computed(() => !sessionUser.isGuest)

const actionOptions = computed<DropdownOptions>(() => [
  {
    group: 'create',
    hideLabel: true,
    options: [
      {
        label: 'New space',
        icon: 'lucide-plus',
        onClick: () => emit('new-space'),
        condition: () => canCreateSpace.value,
      },
    ],
  },
  {
    group: 'manage',
    hideLabel: true,
    options: [
      {
        label: 'Manage spaces',
        icon: 'lucide-layout-grid',
        onClick: () => showCommunitiesSettings(communityId.value, 'spaces'),
        condition: () => canManageCurrentCommunity.value,
      },
      {
        label: 'Manage users',
        icon: 'lucide-users-2',
        onClick: () => showCommunitiesSettings(communityId.value, 'members'),
        condition: () => canManageCurrentCommunity.value,
      },
      {
        label: 'Sort spaces',
        icon: 'lucide-arrow-up-down',
        submenu: spaceSortMenuOptions.value,
      },
    ],
  },
  {
    group: 'share',
    hideLabel: true,
    options: [
      {
        label: 'Copy link',
        icon: 'lucide-link',
        onClick: copyCommunityLink,
      },
      {
        label: 'Mark all as read...',
        icon: 'lucide-check',
        onClick: openMarkAllAsReadDialog,
      },
    ],
  },
  {
    group: 'structure',
    hideLabel: true,
    options: [
      {
        label: 'Merge into...',
        icon: 'lucide-merge',
        onClick: () => (showMergeDialog.value = true),
        condition: () => canManageCurrentCommunity.value,
      },
      {
        label: 'Archive community',
        icon: 'lucide-archive',
        onClick: confirmArchiveCommunity,
        condition: () => canManageCurrentCommunity.value,
      },
    ],
  },
])

// Flatten the groups: the palette has no notion of a section, and its own grouping
// puts every one of these under "Community" anyway.
const paletteActions = computed(() =>
  actionOptions.value.flatMap((group) => ('options' in group ? group.options ?? [] : [group])),
)

useCommandPaletteCommands(
  computed(() =>
    paletteActions.value
      // A submenu has no action of its own, so there is nothing for the palette to run.
      .filter((action) => !action.submenu)
      .map((action) => ({
        title: action.label.replace(/\.\.\.$/, ''),
        name: `community-${action.label.toLowerCase().replace(/\W+/g, '-')}`,
        group: 'Community',
        icon: action.icon,
        aliases: communityActionAliases(action.label),
        onClick: action.onClick,
        condition: action.condition,
        defaultScore: 2,
      })),
  ),
)

function communityActionAliases(label: string) {
  if (label.startsWith('New space')) return ['create space', 'add space']
  if (label.startsWith('Manage spaces')) return ['spaces settings', 'configure spaces']
  if (label.startsWith('Manage users')) return ['members', 'invite users', 'community members']
  if (label.startsWith('Copy link')) return ['copy url', 'share community']
  if (label.startsWith('Mark all as read')) return ['clear unread', 'read all']
  if (label.startsWith('Merge into')) return ['combine communities']
  if (label.startsWith('Archive community')) return ['hide community']
  return []
}

function copyCommunityLink() {
  if (!communityId.value) return
  const route = router.resolve({
    name: 'Discussions',
    params: { communityId: communityId.value },
  })
  copyToClipboard(new URL(route.href, window.location.origin).toString())
}

function openMarkAllAsReadDialog() {
  today.value = dayjsLocal().format('YYYY-MM-DD')
  markReadBeforeDate.value = today.value
  showMarkAllAsReadDialog.value = true
}

async function markAllAsRead() {
  const team = communityId.value
  if (!team) return

  markingAllAsRead.value = true
  try {
    await markCommunityAsRead(team, markReadBeforeDate.value)
    reloadDiscussionLists()
    showMarkAllAsReadDialog.value = false
  } finally {
    markingAllAsRead.value = false
  }
}

function confirmArchiveCommunity() {
  dialog.confirm({
    title: 'Archive community',
    message:
      'Archived communities are hidden from active lists and new work should happen elsewhere. You can unarchive this community later from Settings.',
    confirmLabel: 'Archive',
    onConfirm: archiveCommunity,
  })
}

async function archiveCommunity() {
  const team = communityId.value
  if (!team) return

  await teams.runDocMethod.submit({ name: team, method: 'archive' })
  await communities.reload()
  // The sidebar is scoped to the community that was just archived, so it can't stay here.
  goToCommunity(activeCommunities.value[0]?.name ?? null)
}

function goToCommunity(communityId: string | null) {
  communityState.change(communityId)
  router.push(
    communityId ? { name: 'Discussions', params: { communityId } } : { name: 'NoCommunities' },
  )
}
</script>
