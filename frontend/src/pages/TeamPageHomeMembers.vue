<template>
  <div>
    <div class="flex items-center space-x-2">
      <h2 class="text-2xl font-bold text-gray-900">Members</h2>
      <Button icon="plus" @click="inviteMemberDialog = true" />
    </div>
    <div class="mt-5 space-y-4 rounded-xl">
      <div
        class="flex items-center space-x-2"
        v-for="member in members"
        :title="member.full_name || member.email"
        :key="member.name"
      >
        <Avatar
          :imageURL="member.user_image"
          :label="member.full_name || member.email"
          :title="member.full_name || member.email"
        />
        <div>
          <div class="text-base text-gray-900">
            {{ member.full_name }}
          </div>
          <div class="text-sm text-gray-600">{{ member.email }}</div>
        </div>
      </div>
      <div v-if="!team.doc.members.length" class="text-base text-gray-600">
        Invite members to collaborate.
      </div>
    </div>
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
  computed: {
    members() {
      return this.team.doc.members.filter(
        (member) => member.status != 'Invited'
      )
    },
  },
}
</script>
