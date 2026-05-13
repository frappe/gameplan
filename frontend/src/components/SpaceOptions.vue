<template>
  <DropdownMoreOptions
    :label="`${space?.title} Space Options`"
    v-bind="$attrs"
    :options="options"
  />

  <MergeSpaceDialog v-model="showSpaceMergeDialog" :spaceId="props.spaceId" />
  <ChangeSpaceCategoryDialog v-model="showSpaceCategoryDialog" :spaceId="props.spaceId" />
  <EditSpaceDialog v-model="showSpaceEditDialog" :spaceId="props.spaceId" />
  <ManageMembersDialog v-model="inviteGuestDialog" :spaceId="props.spaceId" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDoctype, dialog } from 'frappe-ui'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import MergeSpaceDialog from './MergeSpaceDialog.vue'
import ChangeSpaceCategoryDialog from './ChangeSpaceCategoryDialog.vue'
import EditSpaceDialog from './EditSpaceDialog.vue'
import ManageMembersDialog from './ManageMembersDialog.vue'
import { useSpace, hasJoined, joinSpace, leaveSpace } from '@/data/spaces'
import { markSpaceAsRead } from '@/data/unreadCount'
import { GPProject } from '@/types/doctypes'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps<{
  spaceId: string
}>()

const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

const showSpaceMergeDialog = ref(false)
const showSpaceCategoryDialog = ref(false)
const showSpaceEditDialog = ref(false)
const inviteGuestDialog = ref(false)

const options = computed(() => [
  {
    label: 'Edit',
    icon: 'lucide-edit',
    onClick: () => (showSpaceEditDialog.value = true),
    condition: () => !space.value?.archived_at,
  },
  {
    label: 'Mark all as read',
    icon: 'lucide-check',
    onClick: () => {
      dialog.confirm({
        title: 'Are you sure?',
        message:
          'This action will mark all discussions in this space as read. This action cannot be undone.',
        confirmLabel: 'Mark all as read',
        onConfirm: () => markSpaceAsRead(props.spaceId),
      })
    },
    condition: () => !space.value?.archived_at,
  },
  {
    label: hasJoined(props.spaceId) ? 'Leave space' : 'Join space',
    icon: hasJoined(props.spaceId) ? 'lucide-log-out' : 'lucide-log-in',
    onClick: () => {
      if (space.value) {
        if (hasJoined(props.spaceId)) {
          leaveSpace(space.value)
        } else {
          joinSpace(space.value)
        }
      }
    },
    condition: () => !space.value?.archived_at,
  },
  {
    label: 'Manage Members',
    icon: 'lucide-user-plus',
    onClick: () => (inviteGuestDialog.value = true),
    condition: () => !space.value?.archived_at,
  },
  {
    label: 'Change Category',
    icon: 'lucide-log-out',
    onClick: () => (showSpaceCategoryDialog.value = true),
    condition: () => !space.value?.archived_at,
  },
  {
    label: 'Merge',
    icon: 'lucide-merge',
    onClick: () => (showSpaceMergeDialog.value = true),
  },
  {
    label: 'Archive',
    icon: 'lucide-archive',
    onClick: () => {
      dialog.confirm({
        title: 'Archive space',
        message:
          'You cannot create new discussions, pages or tasks in an archived space. It will remain read-only. You can unarchive it again at any time.',
        confirmLabel: 'Archive',
        onConfirm: () => spaces.runDocMethod.submit({ method: 'archive', name: props.spaceId }),
      })
    },
    condition: () => !space.value?.archived_at,
  },
  {
    label: 'Delete',
    icon: 'lucide-trash-2',
    onClick: () => {
      let message = `This will permanently delete the space and all its content. This action cannot be undone.`
      if (space.value?.discussions_count && space.value?.tasks_count) {
        message = `This will permanently delete the space and all its content. This space has ${space.value?.discussions_count} discussions and ${space.value?.tasks_count} tasks. This action cannot be undone.`
      } else if (space.value?.discussions_count) {
        message = `This will permanently delete the space and all its content. This space has ${space.value?.discussions_count} discussions. This action cannot be undone.`
      }
      dialog.danger({
        title: 'Delete space',
        message,
        onConfirm: () => spaces.delete.submit({ name: props.spaceId }),
      })
    },
    condition: () => !space.value?.archived_at,
  },
])
</script>
