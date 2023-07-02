<template>
  <div class="py-6">
    <div class="mb-4.5 flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">Tasks</h2>
      <div class="flex items-stretch space-x-2">
        <Select
          :options="[
            { label: 'All', value: 'all' },
            { label: 'Active', value: 'active' },
            { label: 'Done', value: 'done' },
            { label: 'Canceled', value: 'canceled' },
          ]"
          v-model="_listType"
        />
        <Button variant="solid" @click="showNewTaskDialog">
          <template #prefix>
            <LucidePlus class="h-4 w-4" />
          </template>
          Add new
        </Button>
      </div>
    </div>
    <TaskList :listOptions="{ filters }" />
    <NewTaskDialog ref="newTaskDialog" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { Select, getCachedListResource } from 'frappe-ui'
import { getUser } from '@/data/users'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  listType: {
    type: String,
    required: true,
  },
})

const router = useRouter()

const validListTypes = ['active', 'done', 'canceled', 'all']
let _listType = computed({
  get() {
    if (!validListTypes.includes(props.listType)) {
      _listType.value = 'active'
      return 'active'
    }
    return props.listType
  },
  set(value) {
    if (!validListTypes.includes(value)) {
      value = 'active'
    }
    router.replace({
      name: 'ProjectTasks',
      params: {
        teamId: props.project.doc.team,
        projectId: props.project.doc.name,
        listType: value,
      },
    })
  },
})
let newTaskDialog = ref(null)

const filters = computed(() => {
  let sessionUser = getUser('sessionUser').name
  let filters = {
    assigned_or_owner: sessionUser,
  }
  if (props.listType === 'active') {
    filters.status = ['in', ['Backlog', 'Todo', 'In Progress']]
  } else if (props.listType === 'done') {
    filters.status = 'Done'
  } else if (props.listType === 'canceled') {
    filters.status = 'Canceled'
  }
  return filters
})

function showNewTaskDialog() {
  let status = 'Backlog'
  if (props.listType === 'active') {
    status = 'Todo'
  } else if (props.listType === 'done') {
    status = 'Done'
  }
  newTaskDialog.value.show({
    defaults: {
      status,
      assigned_to: getUser('sessionUser').name,
    },
    onSuccess: () => {
      let listOptions = { filters: filters.value }
      let tasks = getCachedListResource(['Tasks', listOptions])
      tasks.reload()
    },
  })
}
</script>
