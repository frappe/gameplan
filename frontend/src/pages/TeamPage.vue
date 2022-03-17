<template>
  <div class="h-full" v-if="$resources.team.doc">
    <router-view :team="$resources.team" />
  </div>
</template>
<script>
export default {
  name: 'TeamPage',
  props: ['teamId'],
  resources: {
    team() {
      return {
        type: 'document',
        doctype: 'Team',
        name: this.teamId,
        whitelistedMethods: {
          inviteMembers: 'invite_members',
        },
      }
    },
  },
}
</script>
