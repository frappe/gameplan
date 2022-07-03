<template>
  <div class="px-6 mt-6">
    <div class="grid grid-cols-8 gap-6">
      <div class="col-span-6 space-y-5">
        <ProjectDetailOverviewSummary :project="project" />
        <ProjectDetailOverviewReadme :project="project" />
      </div>
      <!-- <ProjectDetailOverviewMembers class="col-span-2" :project="project" /> -->
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
