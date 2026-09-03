<template>
  <div class="flex h-full flex-1" v-if="task.doc">
    <div class="w-full flex-1">
      <div class="relative p-3 sm:p-6">
        <div class="absolute right-0 top-0 p-6" v-show="task.setValue.loading">
          <LoadingText v-if="!task.setValue.error" text="Saving..." />
          <ErrorMessage :message="task.setValue.error" />
        </div>
        <div class="mb-2 flex items-center justify-between space-x-2">
          <input
            type="text"
            placeholder="Title"
            class="-ml-0.5 w-full rounded-1 border-none p-0.5 text-4xl-semibold bg-surface-base text-ink-gray-8 focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
            :readonly="!canEditTask"
            @blur="
              canEditTask
                ? task.setValue.submit({
                    title: ($event.target as HTMLInputElement).value,
                  })
                : null
            "
            v-model="task.doc.title"
            v-focus
          />
          <DropdownMoreOptions
            v-if="canEditTask"
            align="end"
            :options="[
              {
                label: 'Delete',
                onClick: deleteTask,
                condition: () => canEditTask && canDeleteContent(task.doc, space, useSessionUser()),
              },
            ]"
          />
        </div>
        <TaskDescriptionEditor
          ref="description"
          editor-class="prose-v3 max-w-none focus-within:ring-2 focus-within:ring-outline-gray-3 rounded-1 p-0.5 -ml-0.5 min-h-[4rem]"
          placeholder="Description"
          :content="task.doc.description"
          :editable="canEditTask"
          @blur="
            canEditTask && !$refs.description.editor.isEmpty
              ? task.setValue.submit({
                  description: $refs.description.editor.getHTML(),
                })
              : null
          "
        />
        <div class="mt-8 flex flex-wrap items-center gap-2 sm:hidden">
          <Combobox
            placeholder="Assign a user"
            :options="assignableUsers"
            :modelValue="task.doc.assigned_to"
            :disabled="!canEditTask"
            @update:modelValue="changeAssignee"
          />
          <DatePicker
            v-model="task.doc.due_date"
            variant="subtle"
            placeholder="Due date"
            format="D MMM, YYYY"
            :disabled="!canEditTask"
            @update:modelValue="
              task.setValue.submit({
                due_date: $event,
              })
            "
          />
          <Dropdown :options="statusOptions" :disabled="!canEditTask">
            <Button :disabled="!canEditTask">
              <template #prefix>
                <TaskStatusIcon :status="task.doc.status" />
              </template>
              {{ task.doc.status || 'Set status' }}
            </Button>
          </Dropdown>
          <Dropdown :options="priorityOptions" :disabled="!canEditTask">
            <Button :disabled="!canEditTask">
              <template v-if="task.doc.priority" #prefix>
                <TaskPriorityIcon :priority="task.doc.priority" />
              </template>
              {{ task.doc.priority || 'Set priority' }}
            </Button>
          </Dropdown>
          <Combobox
            placeholder="Select space"
            :options="spaceOptions"
            :modelValue="task.doc.project"
            :disabled="!canEditTask"
            @update:modelValue="changeSpace"
          />
        </div>
        <CommentsList
          class="mt-8"
          doctype="GP Task"
          :name="taskId"
          :space="space"
          :read-only-mode="readOnlyMode"
        />
      </div>
    </div>
    <div class="hidden w-[20rem] shrink-0 border-l sm:block">
      <div class="grid grid-cols-2 items-center gap-y-6 p-6 text-base text-ink-gray-6">
        <div>Assignee</div>
        <div>
          <Combobox
            class="w-full"
            placeholder="Assign a user"
            :options="assignableUsers"
            :modelValue="task.doc.assigned_to"
            :disabled="!canEditTask"
            @update:modelValue="changeAssignee"
            align="end"
          >
            <template #item-prefix="{ item }">
              <UserAvatar :user="item.value" size="xs" />
            </template>
          </Combobox>
        </div>
        <div>Due Date</div>
        <div>
          <DatePicker
            v-model="task.doc.due_date"
            variant="subtle"
            placeholder="Due date"
            format="D MMM, YYYY"
            align="end"
            :disabled="!canEditTask"
            @update:modelValue="
              task.setValue.submit({
                due_date: $event,
              })
            "
          />
        </div>
        <div>Space</div>
        <div>
          <Combobox
            class="w-full"
            placeholder="Select space"
            align="end"
            :options="spaceOptions"
            :modelValue="task.doc.project"
            :disabled="!canEditTask"
            @update:modelValue="changeSpace"
          />
        </div>
        <div>Status</div>
        <div>
          <!-- statusOptions carry an onClick for the mobile Dropdown; Select ignores it, so
               the desktop control has to persist the change itself. -->
          <Select
            v-model="task.doc.status"
            :options="statusOptions"
            placeholder="Set status"
            :disabled="!canEditTask"
            @update:modelValue="task.setValue.submit({ status: $event })"
          >
            <template #item-prefix="{ item }">
              <TaskStatusIcon :status="item.value" />
            </template>
          </Select>
        </div>
        <div>Priority</div>
        <div>
          <Select
            v-model="task.doc.priority"
            :options="priorityOptions"
            placeholder="Set priority"
            :disabled="!canEditTask"
            @update:modelValue="task.setValue.submit({ priority: $event })"
          >
            <template #item-prefix="{ item }">
              <TaskPriorityIcon :priority="item.value" />
            </template>
          </Select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TaskDescriptionEditor from '@/components/editor/TaskDescriptionEditor.vue'
import CommentsList from '@/components/CommentsList.vue'
import TaskStatusIcon from '@/components/NewTaskDialog/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/icons/TaskPriorityIcon.vue'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import { LoadingText, DatePicker, Button, Combobox, Select, dialog } from 'frappe-ui'
import { vFocus } from '@/directives'
import { activeUsers } from '@/data/users'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { getSpace, useSpace } from '@/data/spaces'
import { useTask } from '@/data/tasks'
import { GPTask } from '@/types/doctypes'
import { useSessionUser } from '@/data/users'
import { canDeleteContent, canEditContent } from '@/utils/permissions'
import { spaces } from '@/data/spaces'
import { useCommandPaletteCommands } from './CommandPalette/registry'

const props = defineProps<{
  taskId: string
  readOnlyMode?: boolean
}>()

const router = useRouter()
const route = useRoute()

const task = useTask(() => props.taskId)
// `useSpace` rather than a bare `getSpace`, which throws on an undefined id. `canEditTask`
// reads this, and the palette command conditions read `canEditTask` while the task the route
// just moved to still has no document.
const space = useSpace(() => task.doc?.project)
const canEditTask = computed(
  () => !props.readOnlyMode && canEditContent(task.doc, space.value, useSessionUser()),
)

function deleteTask() {
  if (!canEditTask.value) return

  dialog.danger({
    title: 'Delete task',
    message: 'Are you sure you want to delete this task?',
    onConfirm: async () => {
      await task.delete.submit()
      router.back()
    },
  })
}

// Watched rather than registered through `task.onSuccess`. The task routes reuse this
// component across tasks, and each task has its own shared entry, so a callback registered
// during setup would stay on the first task's entry and leave every later task unvisited.
watch(
  () => task.doc?.name,
  (name) => {
    if (!name) return
    if (['Task', 'SpaceTask'].includes(route.name as string) && route.params.taskId === name) {
      task.trackVisit.submit()
    }
  },
  { immediate: true },
)

const assignableUsers = computed<{ label: string; value: string }[]>(() => {
  return [
    {
      label: 'No Assignee',
      value: '<no_assignee>',
    },
  ].concat(
    ...activeUsers.value.map((user) => ({
      label: user.full_name,
      value: user.name,
    })),
  )
})

const statusOptions = computed(() =>
  (['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'] as Array<GPTask['status']>).map(
    (status) => ({
      icon: () => h(TaskStatusIcon, { status }),
      label: status,
      value: status,
      onClick: () => canEditTask.value && task.setValue.submit({ status }),
    }),
  ),
)

const priorityOptions = computed(() =>
  (['Low', 'Medium', 'High'] as Array<GPTask['priority']>).map((priority) => ({
    icon: () => h(TaskPriorityIcon, { priority }),
    label: priority,
    value: priority,
    onClick: () => canEditTask.value && task.setValue.submit({ priority }),
  })),
)

const spaceOptions = useGroupedSpaceOptions({ filterFn: (space) => !space.archived_at })

useCommandPaletteCommands(
  computed(() => {
    if (!task.doc || !canEditTask.value) return []

    return [
      ...statusOptions.value.map((status) => ({
        title: `Set status to ${status.label}`,
        name: `task-status-${status.value}`,
        group: 'Task',
        icon: status.icon,
        aliases: ['status', status.label],
        onClick: status.onClick,
        defaultScore: task.doc?.status === status.value ? 0 : 2,
      })),
      ...priorityOptions.value.map((priority) => ({
        title: `Set priority to ${priority.label}`,
        name: `task-priority-${priority.value}`,
        group: 'Task',
        icon: priority.icon,
        aliases: ['priority', priority.label],
        onClick: priority.onClick,
        defaultScore: task.doc?.priority === priority.value ? 0 : 2,
      })),
      ...assignableUsers.value.map((user) => ({
        title: user.value === '<no_assignee>' ? 'Clear assignee' : `Assign to ${user.label}`,
        name: `task-assignee-${user.value}`,
        group: 'Task',
        icon: 'lucide-user-round',
        aliases: ['assignee', 'assign', user.label],
        onClick: () => changeAssignee(user.value),
        defaultScore: task.doc?.assigned_to === user.value ? 0 : 1,
      })),
      ...spaces.data
        .filter((space) => !space.archived_at && space.name !== task.doc?.project)
        .map((space) => ({
          title: `Move task to ${space.title}`,
          name: `task-space-${space.name}`,
          group: 'Task',
          icon: 'lucide-log-out',
          aliases: ['move task', 'change space', space.title, space.team_title],
          onClick: () => changeSpace(space.name),
          defaultScore: 1,
        })),
      {
        title: 'Delete task',
        name: 'task-delete',
        group: 'Task',
        icon: 'lucide-trash-2',
        aliases: ['remove task'],
        onClick: deleteTask,
        condition: () =>
          canEditTask.value && canDeleteContent(task.doc, space.value, useSessionUser()),
        defaultScore: 1,
      },
    ]
  }),
)

// The combobox emits null while its search text is being cleared, before the user has
// picked anything. Saving that would unassign the task (and log an activity for it) every
// time someone types to filter the list. Clearing is a deliberate choice made through the
// "<no_assignee>" option instead.
function changeAssignee(option: string | null) {
  if (!canEditTask.value || option == null) return
  task.setValue.submit({ assigned_to: option === '<no_assignee>' ? '' : option })
}

function changeSpace(option: string | null) {
  if (!canEditTask.value || !task.doc || option == null) return
  task.doc.project = option
  task.setValue.submit({ project: option }).then(updateRoute)
}

function updateRoute() {
  if (task.doc) {
    router.replace({
      name: task.doc.project ? 'SpaceTask' : 'Task',
      params: task.doc.project
        ? {
            communityId: getSpace(task.doc.project)?.team,
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
