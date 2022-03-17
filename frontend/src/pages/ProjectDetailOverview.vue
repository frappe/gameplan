<template>
  <div class="container mt-6 space-y-6">
    <ProjectDetailOverviewMembers class="w-1/2" :project="project" />
    <ProjectDetailOverviewLinks class="w-1/2" :project="project" />
    <ProjectDetailOverviewStatusUpdate class="w-1/2" :project="project" />
  </div>
</template>
<script>
import ProjectDetailOverviewMembers from './ProjectDetailOverviewMembers.vue'
import ProjectDetailOverviewLinks from './ProjectDetailOverviewLinks.vue'
import ProjectDetailOverviewStatusUpdate from './ProjectDetailOverviewStatusUpdate.vue'

export default {
  name: 'ProjectDetailOverview',
  props: ['project'],
  components: {
    ProjectDetailOverviewLinks,
    ProjectDetailOverviewStatusUpdate,
    ProjectDetailOverviewMembers,
  },
}
</script>
