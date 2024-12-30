<template>
  <div class="mt-5 mx-auto max-w-4xl px-2 sm:px-5" v-if="space.doc">
    <div class="mb-4 px-3 flex items-center justify-between">
      <SpaceTabs :spaceId="space.doc.name" />
      <div class="flex items-stretch space-x-2">
        <Button variant="solid" @click="showNewTaskDialog">
          <template #prefix>
            <LucidePlus class="h-4 w-4" />
          </template>
          Add new
        </Button>
      </div>
    </div>
    <div class="px-3">
      <TaskList :listOptions="listOptions" :groupByStatus="true" />
    </div>
    <NewTaskDialog ref="newTaskDialog" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getCachedListResource, Select } from 'frappe-ui'
import { useUser } from '@/data/users'
import SpaceTabs from '@/components/SpaceTabs.vue'

const props = defineProps({
  space: {
    type: Object,
    required: true,
  },
})

let newTaskDialog = ref(null)
let listOptions = computed(() => ({
  filters: {
    project: props.space.name,
  },
}))

function showNewTaskDialog() {
  newTaskDialog.value.show({
    defaults: {
      project: props.space.name,
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
