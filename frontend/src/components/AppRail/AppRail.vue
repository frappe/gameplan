<template>
  <div
    class="flex h-full w-[50px] shrink-0 flex-col items-center bg-surface-sidebar px-[11px] pb-3 pt-2.5"
    :class="showBorder ? 'border-r' : ''"
  >
    <TooltipProvider :delay-duration="0">
      <div class="flex shrink-0 items-center justify-center mb-3">
        <button
          type="button"
          class="flex size-7 items-center justify-center rounded-[7px] transition"
          :class="isRoute('Home') ? 'bg-surface-base shadow-sm' : 'hover:opacity-90'"
          aria-label="Home"
          @click="goHome"
        >
          <GameplanLogo class="size-7 rounded-[7px]" />
        </button>
      </div>

      <div
        v-if="railCommunities.length"
        class="flex min-h-0 w-full flex-1 flex-col items-center border-t pt-3"
      >
        <div class="flex min-h-0 w-[50px] flex-1 flex-col items-center">
          <div class="relative min-h-0 w-[50px] flex-1">
            <div
              v-if="showTopGradient"
              class="pointer-events-none absolute left-0 top-0 z-10 h-4 w-[50px] bg-gradient-to-b from-surface-sidebar to-transparent"
            />
            <div
              v-if="showBottomGradient"
              class="pointer-events-none absolute bottom-0 left-0 z-10 h-4 w-[50px] bg-gradient-to-t from-surface-sidebar to-transparent"
            />

            <div
              ref="communityScrollEl"
              class="h-full w-[50px] overflow-x-hidden overflow-y-auto pb-3 pt-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              <div class="flex w-[50px] flex-col items-center gap-3">
                <TooltipRoot v-for="community in railCommunities" :key="community.name">
                  <TooltipTrigger as-child>
                    <button
                      type="button"
                      class="relative flex size-7 shrink-0 items-center justify-center text-base rounded-[7px]"
                      :aria-label="communityAriaLabel(community)"
                      :class="
                        isActiveCommunity(community.name)
                          ? 'bg-surface-gray-4'
                          : 'bg-surface-gray-3'
                      "
                      @click="goToCommunity(community)"
                    >
                      <span
                        v-if="isActiveCommunity(community.name)"
                        class="absolute -left-[11px] top-1/2 h-7 w-1 -translate-y-1/2 rounded-r bg-surface-gray-8"
                      />
                      <CommunityImage :community="community" class="size-7 transition" />
                      <UnreadBadge
                        :count="getCommunityUnreadCount(community.name)"
                        :style="currentSidebarBadgeStyle"
                      />
                    </button>
                  </TooltipTrigger>
                  <TooltipBubble side="right">
                    <template #content>
                      <div class="leading-relaxed">
                        <div class="text-base">{{ community.title }}</div>
                        <div
                          v-if="showTooltipUnreadCount(getCommunityUnreadCount(community.name))"
                          class="text-p-sm text-ink-gray-5"
                        >
                          {{ tooltipUnreadCount(getCommunityUnreadCount(community.name)) }}
                        </div>
                      </div>
                    </template>
                  </TooltipBubble>
                </TooltipRoot>
              </div>
            </div>
          </div>

          <TooltipRoot v-if="session.isAuthenticated">
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="sm"
                icon="lucide-settings-2"
                label="Customize sidebar"
                class="mt-3"
                @click="showCustomizeSidebar = true"
              />
            </TooltipTrigger>
            <TooltipBubble side="right">
              <template #content>
                <div class="leading-relaxed">Customize sidebar</div>
              </template>
            </TooltipBubble>
          </TooltipRoot>
        </div>
      </div>

      <div class="mt-0.5 flex w-full flex-col items-center gap-0.5">
        <RailIcon
          v-for="item in mainShortcuts"
          :key="item.label"
          :label="item.label"
          :icon="item.icon"
          :is-active="item.isActive"
          :unread-count="item.unreadCount"
          :badge-style="currentSidebarBadgeStyle"
          @click="goTo(item)"
        />
      </div>

      <div v-if="!railCommunities.length" class="flex-1" />
      <div
        v-if="personalShortcuts.length"
        class="mb-3 mt-3 flex w-full flex-col items-center gap-0.5 border-t py-3"
      >
        <RailIcon
          v-for="item in personalShortcuts"
          :key="item.label"
          :label="item.label"
          :icon="item.icon"
          :is-active="item.isActive"
          :unread-count="item.unreadCount"
          :badge-style="currentSidebarBadgeStyle"
          @click="goTo(item)"
        />
      </div>
      <UserDropdown v-if="session.isAuthenticated">
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
    </TooltipProvider>

    <CustomizeSidebarDialog v-model="showCustomizeSidebar" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TooltipProvider, TooltipRoot, TooltipTrigger } from 'reka-ui'
import { useEventListener, useResizeObserver } from '@vueuse/core'
import { Button, TooltipBubble } from 'frappe-ui'
import type { RouteLocationRaw } from 'vue-router'
import { communityState } from '@/data/communityState'
import { navigationCommunities } from '@/data/communities'
import type { Community } from '@/data/communities'
import { unreadNotifications } from '@/data/notifications'
import { currentSidebarBadgeStyle } from '@/data/sidebarPreferences'
import { getSpaceUnreadCount, spaces } from '@/data/spaces'
import { isGameplanAdmin, useSessionUser } from '@/data/users'
import { session } from '@/data/session'
import { useCanManageCommunities } from '@/composables/useCanManageCommunities'
import { showCommunitiesSettings } from '@/components/Settings'
import { unreadAriaLabel } from '@/utils/formatters'
import CommunityImage from '../CommunityImage.vue'
import GameplanLogo from '../GameplanLogo.vue'
import CustomizeSidebarDialog from './CustomizeSidebarDialog.vue'
import RailIcon from './RailIcon.vue'
import UnreadBadge from './UnreadBadge.vue'
import UserAvatar from '../UserAvatar.vue'
import UserDropdown from '../UserDropdown.vue'

interface RailItem {
  label: string
  icon: string
  isActive: boolean
  route?: RouteLocationRaw
  onClick?: () => void
  unreadCount?: number
}

const route = useRoute()
const router = useRouter()
const sessionUser = useSessionUser()
const showCustomizeSidebar = ref(false)
const communityScrollEl = useTemplateRef<HTMLElement>('communityScrollEl')
const showTopGradient = ref(false)
const showBottomGradient = ref(false)

const props = defineProps<{
  showBorder: boolean
  showCommunityActiveState: boolean
}>()

const isAdmin = computed(() => isGameplanAdmin(sessionUser))

onMounted(() => {
  nextTick(updateCommunityScrollState)
})

useEventListener(() => communityScrollEl.value, 'scroll', updateCommunityScrollState, {
  passive: true,
})
useResizeObserver(() => communityScrollEl.value, updateCommunityScrollState)

const railCommunities = computed(() => navigationCommunities.value)

watch(railCommunities, () => nextTick(updateCommunityScrollState), { flush: 'post' })

const homeRoute = computed<RouteLocationRaw>(() => {
  if (communityState.id) {
    return { name: 'Discussions', params: { communityId: communityState.id } }
  }
  return { name: 'Home' }
})

const adminShortcuts = computed<RailItem[]>(() => {
  if (!canManageCommunities.value) return []

  return [
    {
      label: 'Configure communities',
      icon: 'lucide-building-2',
      onClick: () => showCommunitiesSettings(),
    },
  ]
})

const canManageCommunities = useCanManageCommunities()

const mainShortcuts = computed<RailItem[]>(() => [
  ...(session.canBrowsePublicWeb
    ? []
    : [
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
            'PersonProfileAboutMe',
            'PersonProfilePosts',
            'PersonProfileReplies',
          ),
          route: { name: 'People' },
        },
      ]),
  ...adminShortcuts.value,
])

const personalShortcuts = computed<RailItem[]>(() => {
  if (session.canBrowsePublicWeb) return []

  return [
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
    },
  ]
})

function goTo(item: RailItem) {
  if (item.onClick) {
    item.onClick()
    return
  }

  if (item.route) {
    router.push(item.route)
  }
}

function goToCommunity(community: Community) {
  if (session.canBrowsePublicWeb) {
    communityState.scope(community.name)
  } else {
    communityState.change(community.name)
  }
  router.push({ name: 'Discussions', params: { communityId: community.name } })
}

function isActiveCommunity(communityName: string) {
  return props.showCommunityActiveState && communityName === communityState.id
}

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

function communityAriaLabel(community: Community) {
  return unreadAriaLabel(community.title, getCommunityUnreadCount(community.name))
}

function showTooltipUnreadCount(unreadCount: number) {
  return currentSidebarBadgeStyle.value === 'Dot' && unreadCount > 0
}

function tooltipUnreadCount(unreadCount: number) {
  return `${unreadCount} unread`
}

function goHome() {
  router.push(homeRoute.value)
}

function isRoute(...names: string[]) {
  return names.includes(route.name?.toString() || '')
}
</script>
