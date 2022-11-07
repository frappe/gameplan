<template>
  <router-view
    v-if="$resources.project.doc"
    :team="team"
    :project="$resources.project"
  ></router-view>
</template>
<script>
export default {
  name: 'ProjectLayout',
  props: ['team', 'projectId'],
  resources: {
    project() {
      return {
        type: 'document',
        doctype: 'Team Project',
        name: this.projectId,
        realtime: true,
        whitelistedMethods: {
          moveToTeam: 'move_to_team',
          archive: 'archive',
          unarchive: 'unarchive',
          inviteMembers: 'invite_members',
        },
      }
    },
  },
  pageMeta() {
    return {
      title: `${this.$resources.project.doc.title} - ${this.team.doc.title}`,
      emoji: this.$resources.project.doc.icon,
    }
  },
}
</script>
