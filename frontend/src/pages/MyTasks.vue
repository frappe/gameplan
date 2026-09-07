<template>
  <div>
    <PageHeaderMobile class="sm:hidden" title="Tasks">
      <template #prefix>
        <PageHeaderBackButton :to="{ name: 'More' }" />
      </template>
      <template #suffix>
        <Button
          variant="ghost"
          size="md"
          icon="lucide-plus"
          label="Add task"
          @click="openNewTaskDialog"
        />
      </template>
    </PageHeaderMobile>
    <PageHeader class="hidden sm:flex">
      <Breadcrumbs class="h-7" :items="[{ label: 'My Tasks', route: { name: 'MyTasks' } }]" />
      <Button variant="solid" icon-left="lucide-plus" @click="openNewTaskDialog"> Add new </Button>
    </PageHeader>

    <div class="body-container">
      <div class="flex pt-3 sm:pt-5">
        <TabButtons
          :options="[
            { label: 'All', value: 'all' },
            { label: 'Assigned to me', value: 'assigned' },
            { label: 'Created by me', value: 'owner' },
          ]"
          v-model="currentTab"
        />
      </div>
      <div class="pb-6 mt-3 sm:mt-4">
        <TaskList
          :listOptions="{ filters, pageLength: 999999 }"
          :groupByStatus="true"
          ref="taskList"
        />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, useTemplateRef } from 'vue'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  usePageMeta,
  Breadcrumbs,
  Button,
  TabButtons,
} from 'frappe-ui'
import { useUser } from '@/data/users'
import TaskList from '@/components/TaskList.vue'
import { showNewTaskDialog } from '@/components/NewTaskDialog'

let taskList = useTemplateRef<typeof TaskList>('taskList')
let currentTab = ref('all')

let filters = () => {
  let me = useUser('sessionUser').name
  return {
    all: { assigned_or_owner: me },
    assigned: { assigned_to: me },
    owner: { owner: me },
  }[currentTab.value]
}

function openNewTaskDialog() {
  showNewTaskDialog({
    defaults: {
      assigned_to: useUser('sessionUser').name,
    },
    onSuccess: () => {
      taskList.value?.tasks.reload()
    },
  })
}

usePageMeta(() => {
  return {
    title: 'My Tasks',
  }
})
</script>
