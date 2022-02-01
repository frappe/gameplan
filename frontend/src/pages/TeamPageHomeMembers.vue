<template>
  <div>
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Members</h2>
      <Button icon-left="plus" @click="inviteMemberDialog = true">
        Add Member
      </Button>
    </div>
    <div class="mt-4">
      <ul role="list" class="border-t border-gray-200 divide-y divide-gray-200">
        <li
          v-for="member in team.members"
          :key="member.name"
          class="flex items-center justify-between py-4 space-x-3"
        >
          <UserInfo :email="member.email" v-slot="{ user }">
            <div class="flex items-center flex-1 min-w-0 space-x-3">
              <div class="flex-shrink-0">
                <img
                  v-if="user.user_image"
                  class="w-10 h-10 rounded-full"
                  :src="user.user_image"
                  :alt="user.full_name"
                />
                <div
                  v-else
                  class="flex items-center justify-center w-10 h-10 text-lg text-gray-600 bg-gray-300 rounded-full"
                >
                  {{ user.full_name ? user.full_name[0].toUpperCase() : '' }}
                </div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">
                  {{
                    member.status === 'Invited' ? user.email : user.full_name
                  }}
                </p>
                <p class="text-sm font-medium text-gray-500 truncate">
                  {{ member.role }}
                </p>
              </div>
            </div>
            <div class="flex-shrink-0">
              <Badge v-if="member.status === 'Invited'" color="yellow">
                {{ member.status }}
              </Badge>
            </div>
          </UserInfo>
        </li>
      </ul>
    </div>
    <NewDialog :options="{ title: 'Invite' }" v-model="inviteMemberDialog">
      <template #dialog-content>
        <Input type="text" label="Email" v-model="inviteEmail" />
        <ErrorMessage class="mt-2" :message="$resources.teamInvite.error" />
      </template>
      <template #dialog-actions>
        <Button
          type="primary"
          @click="$resources.teamInvite.submit"
          :loading="$resources.teamInvite.loading"
        >
          Send invitation
        </Button>
      </template>
    </NewDialog>
  </div>
</template>
<script>
import { NewDialog } from 'frappe-ui'

export default {
  name: 'TeamPageHomeMembers',
  props: ['team'],
  components: { NewDialog },
  data() {
    return {
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
