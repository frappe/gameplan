<template>
  <div class="pt-6">
    <div class="space-y-5">
      <ProjectOverviewSummary :project="project" />
      <ProjectOverviewReadme :project="project" />
    </div>
  </div>
</template>
<script>
import ProjectOverviewMembers from './ProjectOverviewMembers.vue'
import ProjectOverviewReadme from './ProjectOverviewReadme.vue'
import ProjectOverviewSummary from './ProjectOverviewSummary.vue'

export default {
  name: 'ProjectOverview',
  props: ['project'],
  components: {
    ProjectOverviewMembers,
    ProjectOverviewReadme,
    ProjectOverviewSummary,
  },
}
</script>
