<template>
  <div class="mt-5 body-container">
    <SpaceHeaderActions>
      <Button
        v-if="canEditSpace"
        variant="solid"
        icon-left="lucide-plus"
        label="New task"
        @click="openNewTaskDialog"
      />
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>
    <TaskList :key="spaceId" :listOptions="{ filters }" :groupByStatus="true" ref="taskList" />
  </div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { Button } from 'frappe-ui'
import { useSessionUser } from '@/data/users'
import SpaceTabs from '@/components/SpaceTabs.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import TaskList from '@/components/TaskList.vue'
import { showNewTaskDialog } from '@/components/NewTaskDialog'
import { useSpace } from '@/data/spaces'
import { readOnlyMode } from '@/data/readOnlyMode'
import { isGuest } from '@/utils/permissions'

const props = defineProps<{
  spaceId: string
}>()

const taskList = useTemplateRef<InstanceType<typeof TaskList>>('taskList')
const space = useSpace(() => props.spaceId)
const canEditSpace = computed(
  () => !readOnlyMode && !space.value?.archived_at && !isGuest(useSessionUser()),
)

const filters = () => ({
  project: props.spaceId,
})

function openNewTaskDialog() {
  showNewTaskDialog({
    defaults: {
      project: props.spaceId,
      assigned_to: useSessionUser().name,
    },
    onSuccess: () => {
      taskList.value?.tasks.reload()
    },
  })
}
</script>
