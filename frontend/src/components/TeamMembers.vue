<template>
  <div class="flex items-center">
    <div class="flex items-center rounded-xl">
      <Button
        v-if="!team.doc.members.length"
        @click="inviteMemberDialog = true"
      >
        <template #prefix><LucideUserPlus class="w-4" /></template>
        Add Members
      </Button>
      <template v-else>
        <button
          class="ml-4 flex items-center rounded-full"
          @click="inviteMemberDialog = true"
        >
          <div
            class="-ml-2 flex items-center rounded-full border-2 border-white"
            v-for="member in members"
            :key="member.name"
          >
            <UserAvatar :user="member.user" />
          </div>
        </button>
      </template>
    </div>
  </div>
  <AddMemberDialog :resource="team" v-model="inviteMemberDialog" />
</template>
<script>
import { Avatar } from 'frappe-ui'
import AddMemberDialog from '@/components/AddMemberDialog.vue'

export default {
  name: 'TeamHomeMembers',
  props: ['team'],
  components: {
    Avatar,
    AddMemberDialog,
  },
  data() {
    return {
      inviteMemberDialog: false,
    }
  },
  computed: {
    members() {
      return this.team.doc.members.filter(
        (member) => member.status != 'Invited'
      )
    },
  },
}
</script>
