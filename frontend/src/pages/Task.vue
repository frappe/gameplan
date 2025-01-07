<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="breadcrumbs" />
    </header>
    <div>
      <TaskDetail :taskId="taskId" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { RouteLocationAsRelative, useRoute } from 'vue-router'
import { Breadcrumbs, usePageMeta } from 'frappe-ui'
import TaskDetail from '@/components/TaskDetail.vue'
import { useTask } from '@/data/tasks'
import { useSpace } from '@/data/spaces'

const props = defineProps<{ taskId: string }>()
const task = useTask(() => props.taskId)
const space = useSpace(() => task.doc?.project)
const route = useRoute()

let breadcrumbs = computed(() => {
  let items: Array<{ label: string; route: RouteLocationAsRelative }> = []
  if (!task.doc?.project) {
    items = [
      {
        label: 'My Tasks',
        route: { name: 'MyTasks' },
      },
      {
        label: task.doc ? task.doc.title : route.params.taskId.toString(),
        route: { name: 'Task' },
      },
    ]
  }
  if (space.value) {
    items = [
      {
        label: 'Spaces',
        route: { name: 'Spaces' },
      },
      {
        label: space.value?.title,
        route: { name: 'Space' },
      },
      {
        label: 'Tasks',
        route: { name: 'SpaceTasks' },
      },
      {
        label: task.doc ? task.doc.title : route.params.taskId.toString(),
        route: { name: 'Task' },
      },
    ]
  }
  return items
})

usePageMeta(() => {
  return {
    title: `${task.doc?.title} | ${space.value?.title || 'My Tasks'}`,
  }
})
</script>
