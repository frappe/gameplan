<template>
  <TaskDetail :taskId="taskId" />
</template>
<script setup>
const props = defineProps({
  taskId: {
    default: null,
    type: [String, Number],
  },
})
</script>
