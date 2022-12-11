<template>
  <div class="flex h-full flex-col" v-if="$resources.team.doc">
    <router-view :team="$resources.team" />
  </div>
</template>
<script>
export default {
  name: 'Team',
  props: ['teamId'],
  resources: {
    team() {
      return {
        type: 'document',
        doctype: 'Team',
        name: this.teamId,
        realtime: true,
        whitelistedMethods: {
          addMembers: 'add_members',
          removeMember: 'remove_member',
          archive: 'archive',
          unarchive: 'unarchive',
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
