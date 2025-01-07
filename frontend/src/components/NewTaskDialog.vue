<template>
  <Dialog
    :options="{
      title: 'New Task',
      actions: [
        {
          label: 'Create',
          variant: 'solid',
          onClick: onCreateClick,
        },
      ],
    }"
    :disableOutsideClickToClose="disableOutsideClickToClose"
    v-model="showDialog"
    @after-leave="newTask = newDraftTask()"
  >
    <template #body-content>
      <div class="space-y-4">
        <FormControl label="Title" v-model="newTask.doc.title" autocomplete="off" required />
        <FormControl label="Description" type="textarea" v-model="newTask.doc.description" />
        <div class="flex space-x-2">
          <Dropdown
            :options="
              statusOptions({
                onClick: (status) => (newTask.doc.status = status),
              })
            "
          >
            <Button>
              <template #prefix>
                <TaskStatusIcon :status="newTask.doc.status" />
              </template>
              {{ newTask.doc.status }}
            </Button>
          </Dropdown>
          <TextInput type="date" placeholder="Set due date" v-model="newTask.doc.due_date" />
          <Autocomplete
            placeholder="Assign a user"
            :options="assignableUsers"
            v-model="newTask.doc.assigned_to"
          />
        </div>
        <ErrorMessage class="mt-2" :message="newTask.error" />
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { Dialog, FormControl, Autocomplete, Dropdown, TextInput } from 'frappe-ui'
import { useNewDoc } from 'frappe-ui/src/data-fetching'
import TaskStatusIcon from './icons/TaskStatusIcon.vue'
import { activeUsers } from '@/data/users'
import { GPTask } from '@/types/doctypes'

const showDialog = ref(false)

const newTask = newDraftTask()

function statusOptions({ onClick }) {
  return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map((status) => {
    return {
      icon: () => h(TaskStatusIcon, { status }),
      label: status,
      onClick: () => onClick(status),
    }
  })
}

const assignableUsers = computed(() => {
  return activeUsers.value.map((user) => ({
    label: user.full_name,
    value: user.name,
  }))
})

let _onSuccess
function show({ defaults, onSuccess } = {}) {
  Object.assign(newTask.doc, defaults || {})
  showDialog.value = true
  _onSuccess = onSuccess
}

function newDraftTask() {
  return useNewDoc<GPTask>('GP Task', {
    title: '',
    description: '',
    status: 'Backlog',
    assigned_to: '',
    project: '',
  })
}

function onCreateClick(close) {
  if (!newTask.doc.title) {
    newTask.error = new Error('Task title is required')
    return
  }
  newTask.doc.assigned_to = newTask.doc.assigned_to?.value

  return newTask.submit().then(() => {
    close()
    _onSuccess()
  })
}

let disableOutsideClickToClose = computed(() => {
  return newTask.loading || newTask.doc?.title != ''
})

defineExpose({ show })
</script>
