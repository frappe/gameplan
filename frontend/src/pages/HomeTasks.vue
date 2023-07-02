<template>
  <div class="py-6">
    <div class="mb-4.5 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">My Tasks</h2>
      <div class="flex items-stretch space-x-2">
        <Button variant="solid" @click="showNewTaskDialog">
          <template #prefix>
            <LucidePlus class="h-4 w-4" />
          </template>
          Add new
        </Button>
      </div>
    </div>
    <TaskList :listOptions="listOptions" :groupByStatus="true" />
    <NewTaskDialog ref="newTaskDialog" />
  </div>
</template>
<script setup>
import { ref, computed } from 'vue'
import { getCachedListResource, usePageMeta } from 'frappe-ui'
import { getUser } from '@/data/users'

let newTaskDialog = ref(null)

let listOptions = computed(() => ({
  filters: { assigned_or_owner: getUser('sessionUser').name },
}))

function showNewTaskDialog() {
  newTaskDialog.value.show({
    defaults: {
      assigned_to: getUser('sessionUser').name,
    },
    onSuccess: () => {
      let tasks = getCachedListResource(['Tasks', listOptions.value])
      if (tasks) {
        tasks.reload()
      }
    },
  })
}

usePageMeta(() => {
  return {
    title: 'My Tasks',
  }
})
</script>
