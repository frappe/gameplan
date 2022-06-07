<template>
  <div class="flex flex-col h-full" v-if="$resources.team.doc">
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
  pageMeta() {
    return {
      title: this.$resources.team.doc.title,
      emoji: this.$resources.team.doc.icon,
    }
  },
}
</script>
