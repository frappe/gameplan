<template>
  <router-link
    v-if="space"
    class="relative rounded-md flex flex-col focus:outline-none focus-visible:ring-outline-gray-3 focus-visible:ring-2 justify-between border p-3 hover:bg-surface-gray-2 group transition-colors"
    :to="{
      name: 'Space',
      params: {
        spaceId: space.name,
      },
    }"
  >
    <div class="flex items-start w-full">
      <div class="inline-flex min-w-0 flex-1 mr-1">
        <span class="text-lg mr-1.5 font-[emoji] leading-5 flex-shrink-0">
          {{ space.icon }}
        </span>
        <span class="text-base leading-5 text-ink-gray-9 font-medium truncate flex-1">
          {{ space.title }}
          <span
            v-if="space.is_private"
            class="lucide-lock h-3 w-3 text-ink-gray-6 inline ml-1 mb-0.5"
          />
        </span>
      </div>
      <div class="ml-auto flex">
        <Badge v-if="getSpaceUnreadCount(space.name) > 0" class="group-hover:bg-surface-white">
          {{ getSpaceUnreadCount(space.name) }}
        </Badge>
      </div>
    </div>
    <div class="mt-1.5 flex items-end justify-between">
      <div class="text-ink-gray-5 text-sm">
        {{ space.team_title }}
      </div>

      <div class="flex absolute bottom-2 right-2 items-center space-x-1" @click.prevent>
        <template v-if="!space.archived_at">
          <Button
            v-if="isPinned(space.name)"
            tooltip="Unpin space"
            variant="ghost"
            class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100 focus:opacity-100"
            @click="unpinSpace(space.name)"
            :loading="isPinActionLoading(space.name)"
          >
            <span class="lucide-pin-off size-4" />
          </Button>
          <Button
            v-else
            tooltip="Pin space"
            size="sm"
            variant="ghost"
            class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100 focus:opacity-100"
            @click="pinSpace(space.name)"
            :loading="isPinActionLoading(space.name)"
          >
            <span class="lucide-pin size-4" />
          </Button>
          <div
            class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100 has-[[data-state=open]]:opacity-100 focus-within:opacity-100"
          >
            <SpaceOptions align="end" :spaceId="space.name" />
          </div>
        </template>
        <template v-else>
          <Tooltip :text="'Unarchive space'">
            <Button
              size="sm"
              icon="lucide-archive-restore"
              @click="unarchiveSpace(space)"
              variant="ghost"
              class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100"
            />
          </Tooltip>
        </template>
      </div>
    </div>
  </router-link>
</template>

<script setup lang="ts">
import { Badge, Button, Tooltip } from 'frappe-ui'
import { getSpaceUnreadCount, unarchiveSpace, useSpace } from '@/data/spaces'
import SpaceOptions from '@/components/SpaceOptions.vue'
import { isPinActionLoading, isPinned, pinSpace, unpinSpace } from '@/data/pinnedSpaces'

interface Props {
  spaceId: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
</script>
