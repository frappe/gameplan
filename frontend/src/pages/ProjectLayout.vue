<template>
  <router-view
    class="flex-1"
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
        doctype: 'GP Project',
        name: this.projectId,
        realtime: true,
        whitelistedMethods: {
          moveToTeam: 'move_to_team',
          archive: 'archive',
          unarchive: 'unarchive',
          inviteMembers: 'invite_members',
          inviteGuest: 'invite_guest',
          removeGuest: 'remove_guest',
          trackVisit: 'track_visit',
          follow: 'follow',
          unfollow: 'unfollow',
        },
        onSuccess() {
          this.$resources.project.trackVisit.submit()
        },
      }
    },
  },
  pageMeta() {
    if (!this.$resources.project.doc) return
    return {
      title: `${this.$resources.project.doc.title} - ${this.team.doc.title}`,
      emoji: this.$resources.project.doc.icon,
    }
  },
}
</script>
