<template>
  <div class="flex mt-4">
    <h2 class="sr-only">Members</h2>
    <button
      class="flex mr-2 space-x-2 rounded-full empty:mr-0 focus:outline-none focus-visible:ring"
      @click="inviteMemberDialog = true"
    >
      <div
        v-for="member in team.doc.members"
        :title="member.full_name || member.email"
        :key="member.name"
      >
        <Avatar
          :imageURL="member.user_image"
          :label="member.full_name || member.email"
          :title="member.full_name || member.email"
        />
      </div>
    </button>
    <button
      class="grid w-8 h-8 border border-gray-500 border-dashed rounded-full opacity-50 hover:opacity-100 place-items-center focus-visible:ring focus:outline-none"
      @click="inviteMemberDialog = true"
    >
      <FeatherIcon name="plus" class="w-4 text-gray-700" />
    </button>
  </div>
  <AddMemberDialog :team="team.doc" v-model="inviteMemberDialog" />
</template>
<script>
import { Dialog, Avatar } from 'frappe-ui'
import AddMemberDialog from '@/components/AddMemberDialog.vue'

export default {
  name: 'TeamPageHomeMembers',
  props: ['team'],
  components: {
    Dialog,
    Avatar,
    AddMemberDialog,
  },
  data() {
    return {
      inviteMemberDialog: false,
    }
  },
}
</script>
