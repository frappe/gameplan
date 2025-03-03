<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <SpaceBreadcrumbs
        v-if="space"
        :spaceId="space.name"
        :items="[
          {
            label: 'Tasks',
            route: { name: 'SpaceTasks' },
          },
          {
            label: task.doc ? task.doc.title : route.params.taskId.toString(),
            route: { name: 'Task' },
          },
        ]"
      />
      <Breadcrumbs
        v-else
        class="h-7"
        :items="[
          {
            label: 'My Tasks',
            route: { name: 'MyTasks' },
          },
          {
            label: task.doc ? task.doc.title : route.params.taskId.toString(),
            route: { name: 'Task' },
          },
        ]"
      />
    </header>
    <div>
      <TaskDetail :taskId="taskId" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Breadcrumbs, usePageMeta } from 'frappe-ui'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import { useTask } from '@/data/tasks'
import { useSpace } from '@/data/spaces'

const props = defineProps<{ taskId: string }>()
const task = useTask(() => props.taskId)
const space = useSpace(() => task.doc?.project)
const route = useRoute()

usePageMeta(() => {
  return {
    title: `${task.doc?.title} | ${space.value?.title || 'My Tasks'}`,
  }
})
</script>
