<template>
  <span>
    <router-link
      class="hover:text-blue-600"
      :to="{
        name: 'Team',
        params: {
          teamId: discussion.team,
        },
      }"
    >
      {{ teamTitle }}
    </router-link>
    <span class="text-gray-500"> &mdash; </span>
    <router-link
      class="hover:text-blue-600"
      :to="{
        name: 'Project',
        params: {
          teamId: discussion.team,
          projectId: discussion.project,
        },
      }"
    >
      {{ projectTitle }}
    </router-link>
  </span>
</template>
<script>
export default {
  name: 'DiscussionBreadcrumbs',
  props: ['discussion'],
  computed: {
    projectTitle() {
      return (
        this.$getDoc('GP Project', this.discussion.project)?.title ||
        this.discussion.project
      )
    },
    teamTitle() {
      return (
        this.$getDoc('GP Team', this.discussion.team)?.title ||
        this.discussion.team
      )
    },
  },
}
</script>
