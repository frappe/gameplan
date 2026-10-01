<template>
  <div class="mt-5 body-container">
    <SpaceHeaderActions>
      <Button
        v-if="canEditSpace"
        variant="solid"
        icon-left="lucide-plus"
        @click="openNewTaskDialog"
      >
        Add new
      </Button>
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>
    <div>
      <TaskList :key="spaceId" :listOptions="{ filters }" :groupByStatus="true" ref="taskList" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { useUser } from '@/data/users'
import SpaceTabs from '@/components/SpaceTabs.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import TaskList from '@/components/TaskList.vue'
import { showNewTaskDialog } from '@/components/NewTaskDialog'
import { useSpace } from '@/data/spaces'
import { readOnlyMode } from '@/data/readOnlyMode'

const props = defineProps<{
  spaceId: string
}>()

const taskList = useTemplateRef<typeof TaskList>('taskList')
const space = useSpace(() => props.spaceId)
const canEditSpace = computed(() => !readOnlyMode && !space.value?.archived_at)

const filters = () => ({
  project: props.spaceId,
})

function openNewTaskDialog() {
  showNewTaskDialog({
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
