<template>
  <Dropdown
    v-if="visibleOptions.length"
    :button="{ icon: 'lucide-more-horizontal', size: 'xs', variant: 'ghost' }"
    align="end"
    :label="`${user.full_name} Member Options`"
    :options="visibleOptions"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { dialog, Dropdown, useDoctype } from 'frappe-ui'
import { communities } from '@/data/communities'
import type { Community, CommunityMember } from '@/data/communities'
import { useUser } from '@/data/users'
import type { GPTeam } from '@/types/doctypes'

const props = defineProps<{
  community: Community
  member: CommunityMember
  canManage: boolean
}>()

const teams = useDoctype<GPTeam>('GP Team')
const user = computed(() => useUser(props.member.user))
const adminCount = computed(() => {
  return props.community.members.filter((member) => member.is_admin).length
})
const isLastAdmin = computed(() => Boolean(props.member.is_admin && adminCount.value <= 1))
const canUpdateAdminStatus = computed(() => {
  if (!props.canManage || props.community.archived_at) return false
  return !props.member.is_admin || !isLastAdmin.value
})
const canRemoveMember = computed(() => {
  return props.canManage && !props.community.archived_at && !isLastAdmin.value
})

const options = computed(() => [
  {
    label: props.member.is_admin ? 'Remove community admin' : 'Make community admin',
    icon: props.member.is_admin ? 'lucide-shield-minus' : 'lucide-shield-check',
    onClick: () => setCommunityAdmin(!props.member.is_admin),
    condition: () => canUpdateAdminStatus.value,
  },
  {
    label: 'Remove from community',
    icon: 'lucide-user-round-minus',
    onClick: removeMember,
    condition: () => canRemoveMember.value,
  },
])
const visibleOptions = computed(() => {
  return options.value.filter((option) => option.condition())
})

function removeMember() {
  if (!props.canManage) return

  dialog.confirm({
    title: 'Remove member',
    message: `${user.value.full_name} will lose access to private spaces and discussions in this community.`,
    confirmLabel: 'Remove',
    onConfirm: async () => {
      await teams.runDocMethod.submit({
        name: props.community.name,
        method: 'remove_member',
        params: {
          user: props.member.user,
        },
      })
      await communities.reload()
    },
  })
}

function setCommunityAdmin(isAdmin: boolean) {
  if (!props.canManage) return

  dialog.confirm({
    title: isAdmin ? 'Make community admin' : 'Remove community admin',
    message: isAdmin
      ? `${user.value.full_name} will be able to manage users and settings for this community.`
      : `${user.value.full_name} will no longer be able to manage this community.`,
    confirmLabel: isAdmin ? 'Make Admin' : 'Remove Admin',
    onConfirm: async () => {
      await teams.runDocMethod.submit({
        name: props.community.name,
        method: 'set_member_admin',
        params: {
          user: props.member.user,
          is_admin: isAdmin ? 1 : 0,
        },
      })
      await communities.reload()
    },
  })
}
</script>
