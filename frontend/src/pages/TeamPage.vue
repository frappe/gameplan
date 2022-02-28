<template>
  <div class="h-full" v-if="$resources.team.data">
    <router-view v-if="team" :team="$resources.team.data" />
  </div>
</template>
<script>
import Links from '@/components/Links.vue'
export default {
  name: 'TeamPage',
  props: ['teamId'],
  components: {
    Links,
  },
  resources: {
    team() {
      return {
        method: 'teams.api.get_team',
        cache: ['Team', this.teamId],
        params: {
          name: this.teamId,
        },
        auto: true,
      }
    },
  },
  computed: {
    team() {
      return this.$resources.team.data ? this.$resources.team.data : null
    },
  },
}
</script>
