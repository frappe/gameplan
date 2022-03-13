<template>
  <div class="h-full" v-if="$resources.team.doc">
    <router-view v-if="team" :team="$resources.team.doc" />
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
      }
    },
  },
  computed: {
    team() {
      return this.$resources.team.doc
    },
  },
}
</script>
