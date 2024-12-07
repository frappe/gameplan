<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 sm:px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="[{ label: 'My Tasks', route: { name: 'MyTasks' } }]" />
      <Button variant="solid" @click="showNewTaskDialog">
        <template #prefix>
          <LucidePlus class="h-4 w-4" />
        </template>
        Add new
      </Button>
    </header>

    <div class="mx-auto w-full max-w-4xl px-3 sm:px-5">
      <div class="flex pt-3 sm:pt-5">
        <TabButtons
          :buttons="[
            { label: 'All', value: 'all' },
            { label: 'Assigned to me', value: 'assigned' },
            { label: 'Created by me', value: 'owner' },
          ]"
          v-model="currentTab"
        />
      </div>
      <div class="pb-6 mt-3 sm:mt-4">
        <TaskList :listOptions="listOptions" :groupByStatus="true" />
        <NewTaskDialog ref="newTaskDialog" />
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed } from 'vue'
import { getCachedListResource, usePageMeta, Breadcrumbs, TabButtons } from 'frappe-ui'
import { getUser } from '@/data/users'

let newTaskDialog = ref(null)
let currentTab = ref('all')

let listOptions = computed(() => {
  let me = getUser('sessionUser').name
  let filters = {
    all: { assigned_or_owner: me },
    assigned: { assigned_to: me },
    owner: { owner: me },
  }[currentTab.value]
  return { filters }
})

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
