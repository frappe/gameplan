<template>
  <div class="pt-6">
    <div class="space-y-5 pb-40">
      <ProjectOverviewReadme :project="project" />
      <div class="sm:rounded sm:border sm:px-4 sm:py-3">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-xl font-semibold text-ink-gray-7">Discussions</h2>
          <Button :route="{ name: 'ProjectDiscussions' }">View all</Button>
        </div>
        <DiscussionList
          :listOptions="{
            filters: { project: project.doc.name },
            pageLength: 4,
          }"
          :hideLoadMore="true"
        />
      </div>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div class="sm:rounded sm:border sm:px-4 sm:py-3">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-xl font-semibold text-ink-gray-7">Tasks</h2>
            <Button :route="{ name: 'ProjectTasks' }">View all</Button>
          </div>
          <TaskList
            :listOptions="{
              filters: {
                project: project.doc.name,
                status: ['in', ['Backlog', 'Todo', 'In Progress']],
              },
              pageLength: 4,
            }"
          />
        </div>
        <div class="sm:rounded sm:border sm:px-4 sm:py-3">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-xl font-semibold text-ink-gray-7">Pages</h2>
            <Button :route="{ name: 'ProjectPages' }">View all</Button>
          </div>
          <PageList
            :listOptions="{
              filters: {
                project: project.doc.name,
              },
              pageLength: 4,
            }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import ProjectOverviewReadme from './ProjectOverviewReadme.vue'

export default {
  name: 'ProjectOverview',
  props: ['project'],
  components: {
    ProjectOverviewReadme,
  },
}
</script>
