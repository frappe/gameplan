<template>
  <div class="mt-6">
    <div class="space-y-5">
      <ProjectDetailOverviewSummary :project="project" />
      <ProjectDetailOverviewReadme :project="project" />
    </div>
  </div>
</template>
<script>
import ProjectDetailOverviewMembers from './ProjectDetailOverviewMembers.vue'
import ProjectDetailOverviewReadme from './ProjectDetailOverviewReadme.vue'
import ProjectDetailOverviewSummary from './ProjectDetailOverviewSummary.vue'

export default {
  name: 'ProjectDetailOverview',
  props: ['project'],
  components: {
    ProjectDetailOverviewMembers,
    ProjectDetailOverviewReadme,
    ProjectDetailOverviewSummary,
  },
}
</script>
