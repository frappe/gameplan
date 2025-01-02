<template>
  <DropdownMoreOptions v-bind="$attrs" :options="options" />

  <MergeSpaceDialog v-model="showSpaceMergeDialog" :spaceId="props.spaceId" />
  <ChangeSpaceCategoryDialog v-model="showSpaceCategoryDialog" :spaceId="props.spaceId" />
  <EditSpaceDialog v-model="showSpaceEditDialog" :spaceId="props.spaceId" />
  <ManageMembersDialog v-model="inviteGuestDialog" :spaceId="props.spaceId" />
  <SpaceNotificationsDialog v-model="showNotificationsDialog" :spaceId="props.spaceId" />
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import MergeSpaceDialog from './MergeSpaceDialog.vue'
import ChangeSpaceCategoryDialog from './ChangeSpaceCategoryDialog.vue'
import EditSpaceDialog from './EditSpaceDialog.vue'
import ManageMembersDialog from './ManageMembersDialog.vue'
import SpaceNotificationsDialog from './SpaceNotificationsDialog.vue'
import { createDialog } from '@/utils/dialogs'
import { joinedSpaces, useSpace } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { GPProject } from '@/types/doctypes'

import LucideUserPlus from '~icons/lucide/user-plus'
import LucideEdit from '~icons/lucide/edit'
import LucideMerge from '~icons/lucide/merge'
import LucideTrash2 from '~icons/lucide/trash-2'
import LucideLogOut from '~icons/lucide/log-out'
import LucideBell from '~icons/lucide/bell'
import LucideBellOff from '~icons/lucide/bell-off'

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
const showNotificationsDialog = ref(false)

const options = computed(() => {
  const member = space.value?.members.find((member) => member.user === useSessionUser().name)
  const notificationsEnabled = member
    ? Boolean(member.notify_new_posts || member.notify_new_comments)
    : false

  return [
    {
      label: 'Edit',
      icon: LucideEdit,
      onClick: () => (showSpaceEditDialog.value = true),
      condition: () => !space.value?.archived_at,
    },
    {
      label: 'Notifications',
      icon: notificationsEnabled ? LucideBell : LucideBellOff,
      onClick: () => (showNotificationsDialog.value = true),
      condition: () => !space.value?.archived_at && joinedSpaces.data?.includes(props.spaceId),
    },
    {
      label: 'Manage Members',
      icon: LucideUserPlus,
      onClick: () => (inviteGuestDialog.value = true),
      condition: () => !space.value?.archived_at,
    },
    {
      label: 'Change Category',
      icon: LucideLogOut,
      onClick: () => (showSpaceCategoryDialog.value = true),
      condition: () => !space.value?.archived_at,
    },
    {
      label: 'Merge',
      icon: LucideMerge,
      onClick: () => (showSpaceMergeDialog.value = true),
    },
    {
      label: 'Archive',
      icon: LucideTrash2,
      onClick: () => {
        createDialog({
          title: 'Archive space',
          message:
            'You cannot create new discussions, pages or tasks in an archived space. It will remain read-only. You can unarchive it again at any time.',
          actions: [
            {
              label: 'Archive',
              variant: 'solid',
              loading: spaces.runDocMethod.loading,
              onClick: ({ close }) => {
                spaces.runDocMethod
                  .submit({
                    method: 'archive',
                    name: props.spaceId,
                  })
                  .then(close)
              },
            },
          ],
        })
      },
      condition: () => !space.value?.archived_at,
    },
  ]
})
</script>
