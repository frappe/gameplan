<template>
  <div class="flex mt-4">
    <h2 class="sr-only">Members</h2>
    <button
      class="flex mr-2 space-x-2 rounded-full empty:mr-0 focus:outline-none focus-visible:ring"
      @click="manageMembersDialog = true"
    >
      <div
        :title="member.full_name || member.email"
        v-for="member in team.members"
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
  <Dialog
    :options="{ title: 'Manage team members' }"
    v-model="manageMembersDialog"
  >
    <template #body-content>
      <ul role="list" class="divide-y">
        <li
          class="flex items-center w-full py-2 space-x-2"
          v-for="member in team.members"
          :key="member.name"
        >
          <Avatar
            :imageURL="member.user_image"
            :label="member.full_name || member.email"
          />
          <div>
            <div class="text-base font-medium text-gray-800">
              {{ member.full_name || member.email }}
            </div>
            <div class="text-sm text-gray-600">
              {{ member.full_name ? member.email : '' }}
            </div>
          </div>
          <Badge class="!ml-auto" v-if="member.status == 'Invited'">
            Pending invite
          </Badge>
        </li>
      </ul>
    </template>
  </Dialog>
  <Dialog :options="{ title: 'Invite' }" v-model="inviteMemberDialog">
    <template #body-content>
      <Input type="text" label="Email" v-model="inviteEmail" />
      <ErrorMessage class="mt-2" :message="$resources.teamInvite.error" />
    </template>
    <template #actions>
      <Button
        appearance="primary"
        @click="$resources.teamInvite.submit"
        :loading="$resources.teamInvite.loading"
      >
        Send invitation
      </Button>
    </template>
  </Dialog>
</template>
<script>
import { Dialog, Avatar } from 'frappe-ui'

export default {
  name: 'TeamPageHomeMembers',
  props: ['team'],
  components: { Dialog, Avatar },
  data() {
    return {
      manageMembersDialog: false,
      inviteMemberDialog: false,
      inviteEmail: '',
    }
  },
  resources: {
    teamInvite() {
      return {
        method: 'teams.api.invite_member',
        params: {
          email: this.inviteEmail,
          team: this.team.name,
        },
        onSuccess() {
          this.inviteEmail = ''
          this.inviteMemberDialog = false
          this.$refetchResource(['team', this.team.name])
        },
      }
    },
  },
}
</script>
