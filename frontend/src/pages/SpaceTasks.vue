<template>
  <div class="mt-5 mx-auto max-w-4xl px-2 sm:px-5">
    <div class="mb-4 px-3 flex items-center justify-between">
      <SpaceTabs :spaceId="spaceId" />
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
      <TaskList :listOptions="{ filters }" :groupByStatus="true" ref="taskList" />
    </div>
    <NewTaskDialog ref="newTaskDialog" />
  </div>
</template>

<script setup lang="ts">
import { useTemplateRef } from 'vue'
import { useUser } from '@/data/users'
import SpaceTabs from '@/components/SpaceTabs.vue'
import NewTaskDialog from '@/components/NewTaskDialog.vue'
import TaskList from '@/components/TaskList.vue'

const props = defineProps<{
  spaceId: string
}>()

const newTaskDialog = useTemplateRef<typeof NewTaskDialog>('newTaskDialog')
const taskList = useTemplateRef<typeof TaskList>('taskList')

const filters = () => ({
  project: props.spaceId,
})

function showNewTaskDialog() {
  if (!newTaskDialog.value) return
  newTaskDialog.value.show({
    defaults: {
      project: props.spaceId,
      assigned_to: useUser('sessionUser').name,
    },
    onSuccess: () => {
      taskList.value?.tasks.reload()
    },
  })
}
</script>
