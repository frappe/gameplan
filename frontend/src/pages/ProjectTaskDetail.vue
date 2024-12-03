<template>
  <TaskDetail :taskId="taskId" />
</template>
<script setup>
import { getCachedDocumentResource, usePageMeta } from 'frappe-ui'

const props = defineProps({
  taskId: {
    default: null,
    type: [String, Number],
  },
})

usePageMeta(() => {
  let task = getCachedDocumentResource('GP Task', props.taskId)
  let project = getCachedDocumentResource('GP Project', task?.doc?.project)
  return {
    title: `${task?.doc?.title} | ${project ? project.doc.title : ''}`,
  }
})
</script>
