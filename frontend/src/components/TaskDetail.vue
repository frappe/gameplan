<template>
  <div class="flex h-full flex-1" v-if="task.doc">
    <div class="w-full flex-1">
      <div class="relative p-6">
        <div class="absolute right-0 top-0 p-6" v-show="task.setValue.loading">
          <LoadingText v-if="!task.setValue.error" text="Saving..." />
          <ErrorMessage :message="task.setValue.error" />
        </div>
        <div class="mb-2 flex items-center justify-between space-x-2">
          <input
            type="text"
            placeholder="Title"
            class="-ml-0.5 w-full rounded-sm border-none p-0.5 text-2xl bg-surface-white font-semibold text-ink-gray-8 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
            @blur="
              task.setValue.submit({
                title: ($event.target as HTMLInputElement).value,
              })
            "
            v-model="task.doc.title"
            v-focus
          />
          <Dropdown
            :options="[
              {
                label: 'Delete',
                onClick: () => {
                  $dialog({
                    title: 'Delete task',
                    message: 'Are you sure you want to delete this task?',
                    actions: [
                      {
                        label: 'Delete',
                        theme: 'red',
                        variant: 'solid',
                        onClick({ close }) {
                          return task.delete.submit().then(() => {
                            close()
                            $router.back()
                          })
                        },
                      },
                    ],
                  })
                },
              },
            ]"
          >
            <Button variant="ghost">
              <template #icon><LucideMoreHorizontal class="h-4 w-4" /></template>
            </Button>
          </Dropdown>
        </div>
        <TextEditor
          ref="description"
          editor-class="prose-sm max-w-none focus-within:ring-2 focus-within:ring-outline-gray-3 rounded-sm p-0.5 -ml-0.5 min-h-[4rem]"
          placeholder="Description"
          :content="task.doc.description"
          :bubbleMenu="true"
          :floatingMenu="true"
          @blur="
            !$refs.description.editor.isEmpty
              ? task.setValue.submit({
                  description: $refs.description.editor.getHTML(),
                })
              : null
          "
        />
        <div class="mt-8 flex flex-wrap items-center gap-2 sm:hidden">
          <Autocomplete
            placeholder="Assign a user"
            :options="assignableUsers"
            v-model="task.doc.assigned_to"
            @update:modelValue="changeAssignee"
          />
          <DatePicker
            v-model="task.doc.due_date"
            variant="subtle"
            placeholder="Due date"
            :disabled="false"
            @update:modelValue="
              task.setValue.submit({
                due_date: $event,
              })
            "
          />
          <Dropdown :options="statusOptions">
            <Button>
              <template #prefix>
                <TaskStatusIcon :status="task.doc.status" />
              </template>
              {{ task.doc.status || 'Set status' }}
            </Button>
          </Dropdown>
          <Dropdown :options="priorityOptions">
            <Button>
              <template v-if="task.doc.priority" #prefix>
                <TaskPriorityIcon :priority="task.doc.priority" />
              </template>
              {{ task.doc.priority || 'Set priority' }}
            </Button>
          </Dropdown>
          <Autocomplete
            placeholder="Select space"
            :options="spaceOptions"
            :modelValue="task.doc.project"
            @update:modelValue="changeSpace"
          />
        </div>
        <CommentsList class="mt-8" doctype="GP Task" :name="taskId" />
      </div>
    </div>
    <div class="hidden w-[20rem] shrink-0 border-l sm:block">
      <div class="grid grid-cols-2 items-center gap-y-6 p-6 text-base text-ink-gray-6">
        <div>Assignee</div>
        <div>
          <Autocomplete
            placeholder="Assign a user"
            :options="assignableUsers"
            v-model="task.doc.assigned_to"
            @update:modelValue="changeAssignee"
          />
        </div>
        <div>Due Date</div>
        <div>
          <DatePicker
            v-model="task.doc.due_date"
            variant="subtle"
            placeholder="Due date"
            :disabled="false"
            @update:modelValue="
              task.setValue.submit({
                due_date: $event,
              })
            "
          />
        </div>
        <div>Space</div>
        <div>
          <Autocomplete
            placeholder="Select space"
            :options="spaceOptions"
            :modelValue="task.doc.project"
            @update:modelValue="changeSpace"
          />
        </div>
        <div>Status</div>
        <div>
          <Dropdown :options="statusOptions">
            <Button>
              <template #prefix>
                <TaskStatusIcon :status="task.doc.status" />
              </template>
              {{ task.doc.status || 'Set status' }}
            </Button>
          </Dropdown>
        </div>
        <div>Priority</div>
        <div>
          <Dropdown :options="priorityOptions">
            <Button>
              <template v-if="task.doc.priority" #prefix>
                <TaskPriorityIcon :priority="task.doc.priority" />
              </template>
              {{ task.doc.priority || 'Set priority' }}
            </Button>
          </Dropdown>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TextEditor from '@/components/TextEditor.vue'
import CommentsList from '@/components/CommentsList.vue'
import TaskStatusIcon from '@/components/NewTaskDialog/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/icons/TaskPriorityIcon.vue'
import { Autocomplete, Dropdown, LoadingText, DatePicker, Button, debounce } from 'frappe-ui'
import { focus as vFocus } from '@/directives'
import { activeUsers } from '@/data/users'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useTask } from '@/data/tasks'
import { GPTask } from '@/types/doctypes'

const props = defineProps<{
  taskId: string
}>()

const router = useRouter()
const route = useRoute()

const task = useTask(() => props.taskId)

task.onSuccess((doc) => {
  if (['Task', 'SpaceTask'].includes(route.name as string) && route.params.taskId === doc.name) {
    task.trackVisit.submit()
  }
})

const assignableUsers = computed(() =>
  activeUsers.value.map((user) => ({
    label: user.full_name,
    value: user.name,
  })),
)

const statusOptions = computed(() =>
  (['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'] as Array<GPTask['status']>).map(
    (status) => ({
      icon: () => h(TaskStatusIcon, { status }),
      label: status,
      onClick: () => task.setValue.submit({ status }),
    }),
  ),
)

const priorityOptions = computed(() =>
  (['Low', 'Medium', 'High'] as Array<GPTask['priority']>).map((priority) => ({
    icon: () => h(TaskPriorityIcon, { priority }),
    label: priority,
    onClick: () => task.setValue.submit({ priority }),
  })),
)

const spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

function changeAssignee(option: { value: string } | null) {
  task.setValue.submit({ assigned_to: option?.value || '' })
}

function changeSpace(option: { value: string } | null) {
  if (!task.doc) return
  task.doc.project = option?.value || undefined
  task.setValue.submit({ project: option?.value || '' }).then(updateRoute)
}

function updateRoute() {
  if (task.doc) {
    router.replace({
      name: task.doc.project ? 'SpaceTask' : 'Task',
      params: task.doc.project
        ? {
            taskId: task.doc.name,
            spaceId: task.doc.project,
          }
        : {
            taskId: task.doc.name,
          },
    })
  }
}
</script>
