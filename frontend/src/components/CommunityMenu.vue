<template>
  <nav>
    <MobileListRow
      v-for="(feed, index) in feeds"
      :key="feed.feedType"
      :border="index > 0"
      :active="!activeSpaceId && activeFeedType === feed.feedType"
      @click="select(feed.route)"
    >
      <template #icon>
        <span :class="[feed.icon, 'size-5 text-ink-gray-6']" aria-hidden="true" />
      </template>
      {{ feed.label }}
      <template #trailing>
        <span v-if="feedUnreadCount(feed.feedType) > 0" class="shrink-0 text-md text-ink-gray-5">
          {{ feedUnreadCount(feed.feedType) }}
        </span>
      </template>
    </MobileListRow>
  </nav>

  <div class="mt-5 px-4 text-md text-ink-gray-5">Spaces</div>

  <nav class="mt-1">
    <MobileListRow
      v-for="(space, index) in communitySpaceList"
      :key="space.name"
      :border="index > 0"
      :active="activeSpaceId === space.name"
      @click="
        select({
          name: 'Space',
          params: { communityId, spaceId: space.name },
        })
      "
    >
      <template #icon>
        <SpaceIcon :icon="space.icon" class="size-5 text-ink-gray-6" />
      </template>
      {{ space.title }}
      <template #trailing>
        <span class="flex w-12 shrink-0 items-center justify-end gap-2">
          <span v-if="getSpaceUnreadCount(space.name) > 0" class="text-md text-ink-gray-5">
            {{ getSpaceUnreadCount(space.name) }}
          </span>
          <span
            v-if="space.is_private"
            class="size-4 text-ink-gray-4 lucide-lock"
            aria-hidden="true"
          />
        </span>
      </template>
    </MobileListRow>

    <div
      v-if="communitySpaceList.length === 0"
      class="px-3 py-3 text-base leading-relaxed text-ink-gray-5"
    >
      {{ emptyMessage }}
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import MobileListRow from '@/components/MobileListRow.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { type FeedType } from '@/data/discussions'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { fetchParticipatingUnreadCount, getParticipatingUnreadCount } from '@/data/unreadCount'

interface Props {
  communityId: string
  /** Highlights the matching feed row when no space is active. */
  activeFeedType?: FeedType
  /** Highlights the matching space row. */
  activeSpaceId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'navigate'): void
}>()

const router = useRouter()

interface FeedRow {
  label: string
  icon: string
  feedType: FeedType
  route: RouteLocationRaw
}

const feeds = computed<FeedRow[]>(() => [
  {
    label: 'All discussions',
    icon: 'lucide-message-square-text',
    feedType: 'recent',
    route: { name: 'Discussions', params: { communityId: props.communityId } },
  },
  {
    label: 'Unread',
    icon: 'lucide-mail-open',
    feedType: 'unread',
    route: {
      name: 'DiscussionsTab',
      params: { communityId: props.communityId, feedType: 'unread' },
    },
  },
  {
    label: 'Participating',
    icon: 'lucide-at-sign',
    feedType: 'participating',
    route: {
      name: 'DiscussionsTab',
      params: { communityId: props.communityId, feedType: 'participating' },
    },
  },
])

const communitySpaceList = computed(() => {
  return (spaces.data || []).filter((space) => {
    return !space.archived_at && space.team === props.communityId
  })
})

// Total unread for the community equals the sum of its spaces' unread counts,
// which matches what the "Unread" feed lists.
const communityUnreadTotal = computed(() => {
  return communitySpaceList.value.reduce(
    (total, space) => total + getSpaceUnreadCount(space.name),
    0,
  )
})

function feedUnreadCount(feedType: FeedType): number {
  if (feedType === 'unread') return communityUnreadTotal.value
  if (feedType === 'participating') return getParticipatingUnreadCount(props.communityId)
  return 0
}

watch(
  () => props.communityId,
  (communityId) => {
    if (communityId) fetchParticipatingUnreadCount(communityId)
  },
  { immediate: true },
)

const archivedCommunitySpaces = computed(() => {
  return (spaces.data || []).filter((space) => {
    return space.archived_at && space.team === props.communityId
  })
})

const emptyMessage = computed(() => {
  if (archivedCommunitySpaces.value.length > 0) {
    return 'All spaces in this community are archived.'
  }

  return 'No spaces in this community yet.'
})

function select(route: RouteLocationRaw) {
  router.push(route)
  emit('navigate')
}
</script>
