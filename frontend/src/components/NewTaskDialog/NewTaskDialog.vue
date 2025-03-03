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
  >
    <template #body-content>
      <div class="space-y-4" v-if="newTask">
        <FormControl
          label="Title"
          v-model="newTask.doc.title"
          autocomplete="off"
          required
          ref="titleInput"
        />
        <FormControl label="Description" type="textarea" v-model="newTask.doc.description" />
        <div class="grid grid-cols-2 gap-2">
          <Autocomplete
            placeholder="Assign a user"
            :options="assignableUsers"
            v-model="newTask.doc.assigned_to"
          >
            <template #prefix>
              <UserAvatar
                class="mr-2"
                size="xs"
                :user="newTask.doc.assigned_to?.value ?? newTask.doc.assigned_to"
              />
            </template>
            <template #item-prefix="{ option }">
              <UserAvatar size="xs" :user="option.value" />
            </template>
          </Autocomplete>
          <TextInput type="date" placeholder="Set due date" v-model="newTask.doc.due_date" />
          <Autocomplete placeholder="Project" :options="spaceOptions" v-model="newTask.doc.project">
            <template #prefix>
              <div class="mr-2 leading-4 font-[emoji]" v-if="newTask.doc.project">
                {{ useSpace(newTask.doc.project?.value ?? newTask.doc.project).value.icon }}
              </div>
            </template>
            <template #item-prefix="{ option }">
              <div class="leading-4 font-[emoji]">{{ option.icon }}</div>
            </template>
          </Autocomplete>
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
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { computed, h, useTemplateRef, watch } from 'vue'
import { Dialog, FormControl, Autocomplete, Dropdown, TextInput } from 'frappe-ui'
import TaskStatusIcon from './TaskStatusIcon.vue'
import { activeUsers } from '@/data/users'
import { GPTask } from '@/types/doctypes'
import { showDialog, newTask, _onSuccess } from './state'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useSpace } from '@/data/spaces'

const titleInput = useTemplateRef('titleInput')
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

function onCreateClick({ close }) {
  if (!newTask.value) return
  if (!newTask.value.doc.title) {
    newTask.value.error = new Error('Task title is required')
    return
  }
  newTask.value.doc.assigned_to = newTask.value.doc.assigned_to?.value

  if (newTask.value.doc.project) {
    newTask.value.doc.project = newTask.value.doc.project?.value
  } else {
    newTask.value.doc.project = ''
  }

  return newTask.value.submit().then((doc) => {
    close()
    _onSuccess.value(doc)
  })
}

let disableOutsideClickToClose = computed(() => {
  return newTask.value?.loading || newTask.value?.doc?.title != ''
})

watch(showDialog, (val) => {
  if (val) {
    setTimeout(() => {
      titleInput.value.$el?.querySelector('input')?.focus()
    }, 100)
  }
})
</script>
