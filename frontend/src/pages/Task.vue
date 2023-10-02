<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="breadcrumbs" />
    </header>
    <div>
      <TaskDetail :taskId="taskId" />
    </div>
  </div>
</template>
<script setup>
import { Breadcrumbs, getCachedDocumentResource } from 'frappe-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
})

let breadcrumbs = computed(() => {
  let route = useRoute()
  let task = getCachedDocumentResource('GP Task', route.params.taskId)
  let items = [
    {
      label: 'My Tasks',
      route: { name: 'MyTasks' },
    },
    {
      label: task?.doc ? task.doc.title : route.params.taskId,
      route: { name: 'Task' },
    },
  ]
  return items
})
</script>
