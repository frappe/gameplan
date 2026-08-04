<template>
  <Rail :class="showBorder ? 'border-r' : ''">
    <!-- Cancel Rail's own top padding and stand exactly one PageHeader tall (min-h-12),
         so the divider below the logo continues the header's bottom border across the
         rail instead of sitting a couple of pixels under it. -->
    <div class="-mt-2.5 flex h-12 shrink-0 items-center justify-center">
      <AppDropdown />
    </div>

    <!-- App-wide destinations sit directly under the logo, so their position never
         shifts with how many communities you belong to. -->
    <div class="flex w-full shrink-0 flex-col items-center gap-0.5 border-t pt-3">
      <RailItem
        v-for="item in shortcuts"
        :key="item.label"
        :label="item.label"
        :description="item.description"
        :icon="item.icon"
        variant="ghost"
        :active="item.isActive"
        :badge="item.unreadCount"
        :badge-style="badgeStyle"
        @click="goTo(item)"
      />
    </div>

    <!-- Community list: a self-scrolling region that fades content under whichever
         edge has more to scroll. `flex-1` lets it absorb the leftover height and
         keeps the avatar pinned to the bottom. The 50px columns bleed the list and
         its gradients edge-to-edge into the rail's gutters. -->
    <div
      v-if="activeCommunities.length"
      class="mb-3 mt-3 flex min-h-0 w-full flex-1 flex-col items-center border-t pt-3"
    >
      <div class="relative min-h-0 w-[50px] flex-1">
        <div
          v-show="showTopGradient"
          class="pointer-events-none absolute left-0 top-0 z-10 h-4 w-[50px] bg-gradient-to-b from-surface-sidebar to-transparent"
        />
        <div
          v-show="showBottomGradient"
          class="pointer-events-none absolute bottom-0 left-0 z-10 h-4 w-[50px] bg-gradient-to-t from-surface-sidebar to-transparent"
        />
        <div
          ref="communityScrollEl"
          class="h-full w-[50px] overflow-y-auto overflow-x-hidden pb-3 pt-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          <div class="flex w-[50px] flex-col items-center gap-3">
            <RailItem
              v-for="community in activeCommunities"
              :key="community.name"
              :label="community.title"
              :active="isActiveCommunity(community.name)"
              :badge="getCommunityUnreadCount(community.name)"
              :badge-style="badgeStyle"
              @click="goToCommunity(community)"
            >
              <CommunityImage :community="community" class="size-7 transition" />
            </RailItem>
          </div>
        </div>
      </div>
    </div>

    <!-- With no communities the scroll region collapses; this spacer keeps the
         avatar pinned to the bottom of the rail. -->
    <div v-else class="flex-1" />

    <UserDropdown>
      <template #trigger="{ open }">
        <button
          type="button"
          class="flex size-7 items-center justify-center rounded-full transition focus-visible:ring-0 focus-visible:focus-ring"
          :class="open ? '' : 'hover:opacity-90'"
        >
          <UserAvatar v-if="sessionUser.name" :user="sessionUser.name" size="md" class="size-7" />
        </button>
      </template>
    </UserDropdown>
  </Rail>

  <CustomizeSidebarDialog v-model="showCustomizeSidebarDialog" />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEventListener, useResizeObserver } from '@vueuse/core'
import { Rail, RailItem } from 'frappe-ui'
import type { RouteLocationRaw } from 'vue-router'
import { communityState } from '@/data/communityState'
import { activeCommunities } from '@/data/communities'
import type { Community } from '@/data/communities'
import { draftCount } from '@/data/drafts'
import { unreadNotifications } from '@/data/notifications'
import { currentSidebarBadgeStyle } from '@/data/sidebarPreferences'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { memberCount, useSessionUser } from '@/data/users'
import AppDropdown from '../AppDropdown.vue'
import CommunityImage from '../CommunityImage.vue'
import CustomizeSidebarDialog from './CustomizeSidebarDialog.vue'
import { showCustomizeSidebarDialog } from './customizeSidebar'
import UserAvatar from '../UserAvatar.vue'
import UserDropdown from '../UserDropdown.vue'

interface RailShortcut {
  label: string
  icon: string
  isActive: boolean
  route: RouteLocationRaw
  /** Second tooltip line, for a count the icon can't show. */
  description?: string
  unreadCount?: number
}

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()

const communityScrollEl = useTemplateRef<HTMLElement>('communityScrollEl')
const showTopGradient = ref(false)
const showBottomGradient = ref(false)

const props = defineProps<{
  showBorder: boolean
  showCommunityActiveState: boolean
}>()

// The library takes a neutral badge style; map Gameplan's preference onto it.
const badgeStyle = computed<'count' | 'dot'>(() =>
  currentSidebarBadgeStyle.value === 'Dot' ? 'dot' : 'count',
)

const shortcuts = computed<RailShortcut[]>(() => [
  {
    label: 'Search',
    icon: 'lucide-search',
    isActive: isRoute('Search'),
    route: { name: 'Search' },
  },
  {
    label: 'People',
    icon: 'lucide-users-2',
    isActive: isRoute(
      'People',
      'PersonProfile',
      'PersonProfileProfile',
      'PersonProfilePosts',
      'PersonProfileReplies',
    ),
    route: { name: 'People' },
    description: countLabel(memberCount.value, 'member'),
  },
  {
    label: 'Notifications',
    icon: 'lucide-bell',
    isActive: isRoute('Notifications'),
    route: { name: 'Notifications' },
    unreadCount: unreadNotifications.data || 0,
  },
  {
    label: 'Drafts',
    icon: 'lucide-pencil-line',
    isActive: isRoute('Drafts'),
    route: { name: 'Drafts' },
    description: countLabel(draftCount.value, 'draft'),
  },
])

/** "3 drafts", "1 draft", or nothing at all when there is no count worth showing. */
function countLabel(count: number, noun: string) {
  if (!count) return undefined
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}

function goTo(item: RailShortcut) {
  router.push(item.route)
}

function goToCommunity(community: Community) {
  communityState.change(community.name)
  router.push({ name: 'Discussions', params: { communityId: community.name } })
}

function isActiveCommunity(communityName: string) {
  return props.showCommunityActiveState && communityName === communityState.id
}

// Sum unread counts per community once per spaces/unread change, instead of
// re-scanning every space for each community on every render.
const unreadByCommunity = computed(() => {
  const totals: Record<string, number> = {}
  for (const space of spaces.data || []) {
    if (space.archived_at || !space.team) continue
    totals[space.team] = (totals[space.team] || 0) + getSpaceUnreadCount(space.name)
  }
  return totals
})

function getCommunityUnreadCount(communityId: string) {
  return unreadByCommunity.value[communityId] ?? 0
}

function isRoute(...names: string[]) {
  return names.includes(route.name?.toString() || '')
}

// Fade the community list under whichever edge still has content to scroll.
function updateCommunityScrollState() {
  const el = communityScrollEl.value
  if (!el) {
    showTopGradient.value = false
    showBottomGradient.value = false
    return
  }

  const maxScrollTop = el.scrollHeight - el.clientHeight
  const hasOverflow = maxScrollTop > 1
  showTopGradient.value = hasOverflow && el.scrollTop > 1
  showBottomGradient.value = hasOverflow && el.scrollTop < maxScrollTop - 1
}

onMounted(() => nextTick(updateCommunityScrollState))
useEventListener(communityScrollEl, 'scroll', updateCommunityScrollState, { passive: true })
useResizeObserver(communityScrollEl, updateCommunityScrollState)
watch(activeCommunities, () => nextTick(updateCommunityScrollState), { flush: 'post' })
</script>
