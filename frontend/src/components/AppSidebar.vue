<template>
  <Sidebar disable-collapse width="14rem">
    <template v-if="communityState.doc">
      <div class="flex shrink-0 items-center p-1.5">
        <CommunityDropdown @new-space="openNewSpaceDialog" />
      </div>

      <!--
        The app owns the scroll region: frappe-ui's ScrollArea keeps the thin,
        auto-hiding overlay scrollbar; padding the viewport gives the active
        row's shadow room so overflow-hidden doesn't clip it.
      -->
      <ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-10">
        <div>
          <div class="flex h-7 items-center justify-between">
            <SidebarLabel>Spaces</SidebarLabel>
            <div v-if="!sessionUser.isGuest" class="flex items-center">
              <Dropdown :options="spaceSortMenuOptions" align="end">
                <template #trigger="{ open }">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon="lucide-arrow-up-down text-ink-gray-5"
                    label="Sort spaces"
                    tooltip="Sort spaces"
                    :active="open || hasCustomSpaceSidebarOptions"
                  />
                </template>
              </Dropdown>
              <Button
                variant="ghost"
                size="sm"
                icon="lucide-plus text-ink-gray-5"
                label="New space"
                @click="openNewSpaceDialog"
              />
            </div>
          </div>

          <nav class="mt-0.5 space-y-0.5">
            <SidebarItem
              v-for="space in spacesList"
              :key="space.name"
              :to="{ name: 'Space', params: { communityId: space.team, spaceId: space.name } }"
              :active="isActiveSpace(space.name)"
            >
              <template #prefix>
                <SpaceIcon :icon="space.icon" class="size-4" />
              </template>

              <span class="flex-1 inline-flex items-center gap-1 truncate text-sm">
                <LucideLock v-if="space.is_private" class="size-3 shrink-0 text-ink-gray-5" />
                {{ space.title }}
              </span>

              <template #suffix>
                <!--
                    Count and options menu share one cell: the count fades out on
                    row hover/focus while the "…" menu fades in. The group is
                    SidebarItem's root (`group/sidebar-item`).
                  -->
                <div class="relative mr-1 flex h-7 w-7 shrink-0 items-center justify-end">
                  <span
                    v-if="getSpaceUnreadCount(space.name) > 0"
                    class="absolute right-1 text-xs text-ink-gray-5 transition-opacity group-hover/sidebar-item:opacity-0 group-focus-within/sidebar-item:opacity-0"
                  >
                    {{ getSpaceUnreadCount(space.name) }}
                  </span>
                  <Dropdown :options="spaceOptions(space)" align="start" side="right">
                    <template #default="{ open }">
                      <Button
                        :variant="open ? 'subtle' : 'ghost'"
                        size="xs"
                        icon="lucide-more-horizontal text-ink-gray-5"
                        :label="`${space.title} options`"
                        class="absolute right-0 -mr-0.5 opacity-0 group-hover/sidebar-item:opacity-100 group-focus-within/sidebar-item:opacity-100"
                        :class="open ? 'opacity-100' : ''"
                      />
                    </template>
                  </Dropdown>
                </div>
              </template>
            </SidebarItem>

            <div
              v-if="spacesList.length === 0"
              class="mt-1 px-2 text-xs leading-relaxed text-ink-gray-5"
            >
              {{ communitySpaces.emptyMessage }}
              <Button
                v-if="communitySpaces.archived.length === 0 && !communitySpaces.hasHiddenInactive"
                size="sm"
                icon-left="lucide-plus"
                class="mt-2"
                @click="openNewSpaceDialog"
              >
                Create a space
              </Button>
            </div>
          </nav>
        </div>
      </ScrollArea>
    </template>
  </Sidebar>

  <NewSpaceDialog
    v-model="showNewSpaceDialog"
    :lockedCommunityId="communityState.id ?? undefined"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button, Dropdown, Sidebar, SidebarItem, SidebarLabel, ScrollArea } from 'frappe-ui'
import { communityState } from '@/data/communityState'
import { communitySpaces } from '@/data/communitySpaces'
import { hasCustomSpaceSidebarOptions, spaceSortMenuOptions } from '@/data/sidebarPreferences'
import { getSpaceUnreadCount, markAllAsRead, type Space } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import CommunityDropdown from './CommunityDropdown.vue'
import NewSpaceDialog from './NewSpaceDialog.vue'
import SpaceIcon from './SpaceIcon.vue'
import LucideLock from '~icons/lucide/lock'

const route = useRoute()
const sessionUser = computed(() => useSessionUser())

const spacesList = computed(() => communitySpaces.list)
const showNewSpaceDialog = ref(false)

const activeSpaceId = computed(() => {
  const routeName = route.name?.toString() || ''
  if (routeName.startsWith('Space') || routeName === 'Discussion') {
    return route.params.spaceId?.toString() || null
  }
  if (routeName === 'NewDiscussion') return routeQueryString(route.query.spaceId)
  return null
})

function isActiveSpace(spaceId: string) {
  return activeSpaceId.value === spaceId
}

function openNewSpaceDialog() {
  showNewSpaceDialog.value = true
}

function spaceOptions(space: Space) {
  return [
    {
      label: 'Mark all as read',
      icon: 'lucide-check',
      onClick: () => markAllAsRead([space.name], space.title),
    },
  ]
}

function routeQueryString(value: unknown): string | null {
  const resolved = Array.isArray(value) ? value[0] : value
  return typeof resolved === 'string' && resolved.length > 0 ? resolved : null
}
</script>
