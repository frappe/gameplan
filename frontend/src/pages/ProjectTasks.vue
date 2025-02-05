<template>
  <div class="py-6">
    <div class="mb-4.5 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-ink-gray-8">Tasks</h2>
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
import { ref } from 'vue'
import { Select, getCachedListResource } from 'frappe-ui'
import { useUser } from '@/data/users'
import { computed } from 'vue'

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
})

let newTaskDialog = ref(null)
let listOptions = computed(() => ({
  filters: {
    project: props.project.name,
  },
}))

function showNewTaskDialog() {
  newTaskDialog.value.show({
    defaults: {
      project: props.project.name,
      assigned_to: useUser('sessionUser').name,
    },
    onSuccess: () => {
      let tasks = getCachedListResource(['Tasks', listOptions.value])
      if (tasks) {
        tasks.reload()
      }
    },
  })
}
</script>
