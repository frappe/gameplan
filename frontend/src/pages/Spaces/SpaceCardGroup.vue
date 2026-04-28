<template>
  <div class="isolate" ref="el">
    <div class="flex items-center gap-2 py-2 bg-surface-white z-[1]">
      <div class="text-base text-ink-gray-8">
        {{ noCategories ? 'All spaces' : group.title || group.name }}
      </div>
      <Badge v-if="isMethodLoading('mark_all_as_read')"> Marking all as read... </Badge>
      <Badge v-else-if="getCategoryUnreadCount(group.name) > 0">
        {{ getCategoryUnreadCount(group.name) }}
      </Badge>
      <DropdownMoreOptions class="ml-auto" align="end" :options="categoryOptions(group)" />
    </div>
    <div class="grid sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      <SpaceCard v-for="(d, index) in group.spaces" :key="d.name" :space="d" />
    </div>
    <EditCategoryDialog ref="editCategoryDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import { Badge } from 'frappe-ui'
import { GroupedSpaceItem, useGroupedSpaces, noCategories } from '@/data/groupedSpaces'
import {
  getSpaceUnreadCount,
  joinSpaces,
  leaveSpaces,
  markAllAsRead,
  isMethodLoading,
} from '@/data/spaces'
import SpaceCard from './SpaceCard.vue'
import EditCategoryDialog from '@/components/EditCategoryDialog.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'

defineProps<{
  group: GroupedSpaceItem
}>()

const emit = defineEmits<{
  'new-space': [categoryName: string]
}>()

const $el = useTemplateRef('el')

defineExpose({
  $el,
})

const groupedSpaces = useGroupedSpaces()
const editCategoryDialog = ref<InstanceType<typeof EditCategoryDialog> | null>(null)

function getCategoryUnreadCount(categoryId: string) {
  let count = 0
  for (const group of groupedSpaces.value) {
    if (group.name === categoryId) {
      for (const space of group.spaces) {
        if (!space.archived_at) {
          count += getSpaceUnreadCount(space.name)
        }
      }
    }
  }
  return count
}

function categoryOptions(group: GroupedSpaceItem) {
  return [
    {
      label: 'Edit',
      condition: () => group.title !== 'Uncategorized',
      onClick: () => {
        editCategoryDialog.value?.openDialog(group)
      },
    },
    {
      label: 'Mark all as read',
      condition: () => group.title !== 'Uncategorized' && group.spaces.length > 0,
      onClick: () =>
        markAllAsRead(
          group.spaces.map((d) => d.name),
          group.title,
        ),
    },
    {
      label: 'Join all',
      onClick: () => joinSpaces(group.spaces.map((d) => d.name)),
    },
    {
      label: 'Leave all',
      onClick: () => leaveSpaces(group.spaces.map((d) => d.name)),
    },
    {
      label: 'New space',
      onClick: () => {
        if (group.title !== 'Uncategorized') {
          emit('new-space', group.name)
        } else {
          emit('new-space', '')
        }
      },
    },
  ]
}
</script>
