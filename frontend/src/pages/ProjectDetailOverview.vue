<template>
  <div class="container mt-6">
    <div class="grid grid-cols-8 gap-6">
      <ProjectDetailOverviewReadme class="col-span-6" :project="project" />
      <ProjectDetailOverviewMembers class="col-span-2" :project="project" />
    </div>
  </div>
</template>
<script>
import ProjectDetailOverviewMembers from './ProjectDetailOverviewMembers.vue'
import ProjectDetailOverviewReadme from './ProjectDetailOverviewReadme.vue'

export default {
  name: 'ProjectDetailOverview',
  props: ['project'],
  components: {
    ProjectDetailOverviewMembers,
    ProjectDetailOverviewReadme,
  },
}
</script>
