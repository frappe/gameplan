<template>
  <TaskDetail :taskId="taskId" />
</template>
<script>
export default {
  name: 'HomeTask',
  props: ['taskId'],
}
</script>
