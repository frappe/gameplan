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
    <div class="mb-4 flex items-center justify-between gap-2">
      <SpaceTabs :spaceId="spaceId" />
      <!-- SpaceHeaderActions sits in the desktop header, so phones get their own button. -->
      <Button
        v-if="canEditSpace"
        class="sm:hidden"
        variant="solid"
        icon-left="lucide-plus"
        label="New"
        @click="openNewTaskDialog"
      />
    </div>
    <!-- Every task in the space, not TaskList's first page: it has no "load more". -->
    <TaskList
      :key="spaceId"
      :listOptions="{ filters, pageLength: 99999 }"
      :groupByStatus="true"
      ref="taskList"
    />
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
