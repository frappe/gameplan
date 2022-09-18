<template>
  <div class="flex items-center">
    <div class="flex items-center rounded-xl">
      <div v-if="!team.doc.members.length" class="mr-2 text-base text-gray-600">
        Invite members to collaborate
      </div>
      <template v-else>
        <span class="hidden text-base text-gray-600 sm:inline">
          {{
            members.length > 1
              ? `${members.length} members`
              : `${members.length} member`
          }}
        </span>
        <button
          class="flex items-center ml-4 rounded-full"
          @click="inviteMemberDialog = true"
        >
          <div
            class="flex items-center -ml-2 border-2 border-white rounded-full"
            v-for="member in members"
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
      </template>
    </div>
    <div class="flex items-center ml-2 space-x-2">
      <Button label="Share" @click="inviteMemberDialog = true" />
    </div>
  </div>
  <AddMemberDialog :team="team.doc" v-model="inviteMemberDialog" />
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
