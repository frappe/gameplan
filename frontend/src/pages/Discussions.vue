<template>
  <MobileHeader v-if="communityState.doc" class="sm:hidden" :title="feedTitle">
    <template #left>
      <MobileBackButton :to="{ name: 'Home' }" label="Communities" />
    </template>
    <button
      type="button"
      class="inline-flex max-w-full items-center gap-1 transition active:opacity-60"
      @click="menuOpen = true"
    >
      <MobileHeaderTitle :title="feedTitle" />
      <span class="size-4 shrink-0 text-ink-gray-5 lucide-chevron-down" aria-hidden="true" />
    </button>
  </MobileHeader>

  <BottomSheet v-model="menuOpen" :title="community?.title || 'Community'">
    <CommunityMenu
      class="pb-6"
      :communityId="communityId"
      :activeFeedType="feedType"
      @navigate="menuOpen = false"
    />
  </BottomSheet>
  <PageHeader class="hidden sm:flex">
    <div class="flex min-w-0 items-center gap-1">
      <router-link
        v-if="community"
        class="min-w-0 truncate rounded px-0.5 py-1 text-lg-medium text-ink-gray-9"
        :title="community.title"
        :to="{ name: 'Discussions', params: { communityId } }"
      >
        {{ community.title }}
      </router-link>
      <Dropdown v-if="visibleActionOptions.length" :options="visibleActionOptions">
        <template #default="{ open }">
          <Button
            :variant="open ? 'subtle' : 'ghost'"
            icon="lucide-more-horizontal"
            label="Community actions"
            :loading="markingAllAsRead"
          />
        </template>
      </Dropdown>
    </div>
    <div class="flex items-center gap-2">
      <Button
        v-if="session.isAuthenticated"
        variant="solid"
        icon-left="lucide-plus"
        :route="{ name: 'NewDiscussion', params: { communityId } }"
      >
        Add new
      </Button>
    </div>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <LastPostReminder v-if="session.isAuthenticated" class="mb-3" />

    <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <TabButtons :options="feedTabs" v-model="currentFeed" size="sm">
        <template #suffix="{ button }">
          <span
            v-if="feedUnreadCount(String(button.value)) > 0"
            class="ml-1 text-xs text-ink-gray-5"
          >
            {{ feedUnreadCount(String(button.value)) }}
          </span>
        </template>
      </TabButtons>
      <Select class="shrink-0 !w-fit" :options="orderOptions" v-model="orderBy" />
    </div>

    <KeepAlive>
      <DiscussionList
        class="-mx-3"
        ref="discussionListRef"
        :filters="filters"
        :orderBy="() => orderBy"
        :cacheKey="`Discussions-${communityId}-${feedType}`"
        :key="JSON.stringify(filters)"
      />
    </KeepAlive>
  </div>

  <Dialog v-model:open="showMarkAllAsReadDialog" title="Mark all as read">
    <div class="space-y-3">
      <p class="text-p-base text-ink-gray-7">
        Mark discussions in {{ community?.title || 'this community' }} as read up to and including
        the selected date. This cannot be undone.
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
      <div class="flex justify-end">
        <Button variant="solid" :loading="markingAllAsRead" @click="markAllAsRead">
          Mark all as read
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import {
  Button,
  DatePicker,
  dayjsLocal,
  Dialog,
  Dropdown,
  Select,
  TabButtons,
  usePageMeta,
} from 'frappe-ui'
import type { DropdownOptions, OrderBy } from 'frappe-ui'
import { useRouter } from 'vue-router'
import BottomSheet from '@/components/BottomSheet.vue'
import CommunityMenu from '@/components/CommunityMenu.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import PageHeader from '@/components/PageHeader.vue'
import LastPostReminder from '@/components/LastPostReminder.vue'
import MobileBackButton from '@/components/MobileBackButton.vue'
import MobileHeader from '@/components/MobileHeader.vue'
import MobileHeaderTitle from '@/components/MobileHeaderTitle.vue'
import { communityState } from '@/data/communityState'
import { useCommunity } from '@/data/communities'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import {
  fetchParticipatingUnreadCount,
  getParticipatingUnreadCount,
  markCommunityAsRead,
} from '@/data/unreadCount'
import { canManageCommunity } from '@/utils/permissions'
import { showCommunitiesSettings } from '@/components/Settings'
import { useCommandPaletteCommands } from '@/components/CommandPalette/registry'
import { session } from '@/data/session'

type FeedType = 'recent' | 'unread' | 'participating'

interface Props {
  communityId: string
  feedType?: FeedType
}

const props = withDefaults(defineProps<Props>(), {
  feedType: 'recent',
})

const orderBy = ref<OrderBy>('last_post_at desc')
const menuOpen = ref(false)
const markingAllAsRead = ref(false)
const showMarkAllAsReadDialog = ref(false)
// Today is the latest allowed cutoff: a future date can't mark not-yet-posted discussions
// read, and the backend clamps to it anyway. Defaults to today so the action clears
// everything unless an earlier date is picked. Held in a ref and refreshed whenever the
// dialog opens so a page left open past midnight still offers the real current day.
const today = ref(dayjsLocal().format('YYYY-MM-DD'))
const markReadBeforeDate = ref(today.value)
const discussionListRef = useTemplateRef('discussionListRef')
const router = useRouter()
const sessionUser = useSessionUser()

const filters = computed(() => ({
  team: props.communityId,
  feed_type: props.feedType,
}))

const feedTitles: Record<FeedType, string> = {
  recent: 'All Discussions',
  unread: 'Unread',
  participating: 'Participating',
}

const feedTitle = computed(() => feedTitles[props.feedType])

const community = useCommunity(() => props.communityId)
const communitySpaces = computed(() => {
  return (spaces.data || []).filter((space) => {
    return !space.archived_at && space.team === props.communityId
  })
})
const communityUnreadCount = computed(() => {
  return communitySpaces.value.reduce((total, space) => total + getSpaceUnreadCount(space.name), 0)
})
const participatingUnreadCount = computed(() => {
  return getParticipatingUnreadCount(props.communityId)
})
const feedTabs = computed(() => [
  {
    label: 'All Discussions',
    value: 'recent',
  },
  ...(session.canBrowsePublicWeb
    ? []
    : [
        {
          label: 'Participating',
          value: 'participating',
        },
        {
          label: 'Unread',
          value: 'unread',
        },
      ]),
])
const currentFeed = computed({
  get() {
    return props.feedType
  },
  set(feedType) {
    if (!feedType || feedType === props.feedType) return
    router.push(feedRoute(String(feedType) as FeedType))
  },
})
const actionOptions = computed<DropdownOptions>(() => [
  {
    label: 'Manage spaces',
    icon: 'lucide-layout-grid',
    onClick: () => showCommunitiesSettings(props.communityId, 'spaces'),
    condition: () => canManageCurrentCommunity.value,
  },
  {
    label: 'Manage users',
    icon: 'lucide-users-2',
    onClick: () => showCommunitiesSettings(props.communityId, 'members'),
    condition: () => canManageCurrentCommunity.value,
  },
  {
    label: 'Mark all as read...',
    icon: 'lucide-check',
    onClick: openMarkAllAsReadDialog,
    condition: () => session.isAuthenticated,
  },
])
const visibleActionOptions = computed<DropdownOptions>(() => {
  return actionOptions.value.filter((action) => !action.condition || action.condition())
})
const canManageCurrentCommunity = computed(() => canManageCommunity(community.value, sessionUser))

useCommandPaletteCommands(
  computed(() =>
    actionOptions.value.map((action) => ({
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
  if (label.startsWith('Manage spaces')) return ['spaces settings', 'configure spaces']
  if (label.startsWith('Manage users')) return ['members', 'invite users', 'community members']
  if (label.startsWith('Mark all as read')) return ['clear unread', 'read all']
  return []
}

watch(
  () => props.communityId,
  (communityId) => {
    if (communityId) fetchParticipatingUnreadCount(communityId)
  },
  { immediate: true },
)

const orderOptions = [
  {
    label: 'Sort by',
    value: '' as const,
    disabled: true,
  },
  {
    label: 'Newest first',
    value: 'last_post_at desc' as OrderBy,
  },
  {
    label: 'Oldest first',
    value: 'last_post_at asc' as OrderBy,
  },
  {
    label: 'Creation date',
    value: 'creation desc' as OrderBy,
  },
]

function feedRoute(feedType: FeedType) {
  if (feedType === 'recent') {
    return { name: 'Discussions', params: { communityId: props.communityId } }
  }

  return {
    name: 'DiscussionsTab',
    params: { communityId: props.communityId, feedType },
  }
}

function feedUnreadCount(feedType: string) {
  if (feedType === 'unread') return communityUnreadCount.value
  if (feedType === 'participating') return participatingUnreadCount.value
  return 0
}

function openMarkAllAsReadDialog() {
  today.value = dayjsLocal().format('YYYY-MM-DD')
  markReadBeforeDate.value = today.value
  showMarkAllAsReadDialog.value = true
}

async function markAllAsRead() {
  markingAllAsRead.value = true
  try {
    await markCommunityAsRead(props.communityId, markReadBeforeDate.value)
    await Promise.all([
      discussionListRef.value?.discussions.reload(),
      discussionListRef.value?.pinnedDiscussions.reload(),
    ])
    showMarkAllAsReadDialog.value = false
  } finally {
    markingAllAsRead.value = false
  }
}

usePageMeta(() => ({ title: feedTitle.value }))
</script>
