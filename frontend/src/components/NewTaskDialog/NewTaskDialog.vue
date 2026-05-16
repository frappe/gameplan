<template>
  <Dialog title="New Task" :dismissable="!disableOutsideClickToClose" v-model:open="showDialog">
    <div class="space-y-4" v-if="newTask">
      <FormControl
        label="Title"
        v-model="newTask.doc.title"
        required
        autofocus
        @keydown.enter="onCreateClick"
      />
      <FormControl
        label="Description"
        type="textarea"
        v-model="newTask.doc.description"
        @keydown.enter="onCreateClick"
      />
      <div class="grid grid-cols-2 gap-2">
        <Combobox
          placeholder="Assign a user"
          :options="assignableUsers"
          v-model="newTask.doc.assigned_to"
        />
        <DatePicker
          v-model="newTask.doc.due_date"
          placeholder="Set due date"
          format="D MMM, YYYY"
        />
        <Combobox
          placeholder="Select space"
          :options="spaceOptions"
          v-model="newTask.doc.project"
        />
        <Dropdown class="w-full" :options="statusOptions()">
          <Button>
            <template #prefix v-if="newTask.doc.status">
              <TaskStatusIcon :status="newTask.doc.status" />
            </template>
            {{ newTask.doc.status }}
          </Button>
        </Dropdown>
      </div>
      <ErrorMessage class="mt-2" :message="newTask.error" />
    </div>

    <template #actions>
      <Button class="w-full relative" variant="solid" @click="onCreateClick">
        Create
        <div class="absolute right-0 top-0 h-7 pr-2 flex items-center justify-center">
          <KeyboardShortcut ctrl> Enter </KeyboardShortcut>
        </div>
      </Button>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, h } from 'vue'
import { Dialog, FormControl, Dropdown, Combobox, DatePicker } from 'frappe-ui'
import TaskStatusIcon from './TaskStatusIcon.vue'
import { activeUsers } from '@/data/users'
import { GPTask } from '@/types/doctypes'
import { showDialog, newTask, _onSuccess } from './state'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import KeyboardShortcut from '../KeyboardShortcut.vue'

let spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

function statusOptions() {
  return (['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'] as GPTask['status'][]).map(
    (status) => {
      return {
        icon: () => h(TaskStatusIcon, { status }),
        label: status,
        onClick: () => {
          if (newTask.value) {
            newTask.value.doc.status = status
          }
        },
      }
    },
  )
}

const assignableUsers = computed(() => {
  return activeUsers.value.map((user) => ({
    label: user.full_name,
    value: user.name,
  }))
})

function onCreateClick(e: KeyboardEvent) {
  if (e instanceof KeyboardEvent && !(e.ctrlKey || e.metaKey)) {
    return
  }

  if (!newTask.value) return
  if (!newTask.value.doc.title) {
    newTask.value.error = new Error('Task title is required')
    return
  }

  return newTask.value.submit().then((doc) => {
    showDialog.value = false
    _onSuccess.value(doc)
  })
}

let disableOutsideClickToClose = computed(() => {
  return newTask.value?.loading || newTask.value?.doc?.title != ''
})
</script>
