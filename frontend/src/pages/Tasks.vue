<template>
  <div class="flex h-full">
    <TasksToDoList class="w-2/6" />
  </div>
</template>
<script>
import TasksToDoList from './TasksToDoList.vue'
export default {
  name: 'Tasks',
  components: { TasksToDoList },
  pageMeta() {
    return {
      title: 'Tasks',
      emoji: '📝',
    }
  },
}
</script>
