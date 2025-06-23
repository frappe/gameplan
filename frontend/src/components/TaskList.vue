<template>
  <div class="@container" v-if="tasks.data?.length">
    <div v-for="group in groupedTasks" :key="group.title">
      <button
        class="group flex w-full items-baseline rounded-sm bg-surface-menu-bar px-2.5 py-2 text-base transition hover:bg-surface-gray-2"
        v-if="group.title && group.tasks.length"
        @click="isOpen[group.title] = !isOpen[group.title]"
      >
        <span class="font-medium text-ink-gray-8">
          {{ group.title }}
        </span>
        <span class="ml-2 text-sm text-ink-gray-5">{{ group.tasks.length }}</span>
        <span class="ml-auto hidden text-sm text-ink-gray-5 group-hover:inline">
          {{ isOpen[group.title] ? 'Collapse' : 'Expand' }}
        </span>
      </button>
      <div :class="{ hidden: !(isOpen[group.title] ?? true) }">
        <div v-for="(d, index) in group.tasks" :key="d.name">
          <router-link
            :to="{
              name: d.project ? 'SpaceTask' : 'Task',
              params: { spaceId: d.project, taskId: d.name },
            }"
            class="flex h-15 w-full items-center rounded p-2.5 transition hover:bg-surface-gray-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 group"
            :class="{
              'pointer-events-none': tasks.delete.loading && tasks.delete.params.name === d.name,
            }"
          >
            <div class="w-full min-w-0">
              <div class="flex min-w-0 items-start">
                <LoadingIndicator
                  class="h-4 w-4 text-ink-gray-5"
                  v-if="tasks.delete.loading && tasks.delete.params.name === d.name"
                />
                <Tooltip text="Change status" v-else>
                  <Dropdown
                    :options="
                      statusOptions({
                        onClick: (status) =>
                          tasks.setValue.submit({
                            status,
                            name: d.name,
                          }),
                      })
                    "
                  >
                    <button
                      class="flex rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
                    >
                      <TaskStatusIcon :status="d.status" />
                    </button>
                  </Dropdown>
                </Tooltip>
                <div
                  class="ml-2.5 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium leading-4 text-ink-gray-8"
                >
                  {{ d.title }}
                </div>
              </div>

              <div class="ml-6.5 mt-1.5 flex items-center">
                <div class="text-base text-ink-gray-5">#{{ d.name }}</div>
                <div
                  v-if="$route.name != 'ProjectOverview' && d.project"
                  class="flex min-w-0 items-center text-base leading-none text-ink-gray-5"
                >
                  <div class="px-2 leading-none text-ink-gray-5">&middot;</div>
                  <div class="overflow-hidden text-ellipsis whitespace-nowrap">
                    {{ d.project_title }}
                  </div>
                </div>
                <div class="hidden items-center @md:flex" v-if="d.assigned_to">
                  <div class="px-2 leading-none text-ink-gray-5">&middot;</div>
                  <span class="whitespace-nowrap text-base text-ink-gray-5">
                    {{ $user(d.assigned_to).full_name }}
                  </span>
                </div>

                <template v-if="d.due_date">
                  <div class="px-2 leading-none text-ink-gray-5">&middot;</div>
                  <div class="flex items-center">
                    <LucideCalendar class="h-3 w-3 text-ink-gray-5" />
                    <span class="ml-2 whitespace-nowrap text-base text-ink-gray-5">
                      {{ dayjsLocal(d.due_date).format('D MMM') }}</span
                    >
                  </div>
                </template>
                <template v-if="d.priority">
                  <div class="px-2 leading-none text-ink-gray-5">&middot;</div>
                  <div class="flex items-center">
                    <div
                      class="h-2 w-2 rounded-full"
                      :class="{
                        'bg-surface-red-5': d.priority === 'High',
                        'bg-surface-amber-5': d.priority === 'Medium',
                        'bg-surface-gray-5': d.priority === 'Low',
                      }"
                    ></div>
                    <span class="ml-2 text-base text-ink-gray-5">
                      {{ d.priority }}
                    </span>
                  </div>
                </template>
              </div>
            </div>
            <div class="sm:invisible group-hover:visible">
              <DropdownMoreOptions :options="dropdownOptions(d.name)" placement="right" />
            </div>
          </router-link>
          <div class="mx-2.5 border-b" v-if="index < group.tasks.length - 1"></div>
        </div>
      </div>
    </div>
  </div>
  <EmptyStateBox v-else>
    <template v-if="tasks.error">
      <ErrorMessage :message="tasks.error" />
    </template>
    <template v-else>
      <LucideCoffee class="h-7 w-7 text-ink-gray-4" />
      No tasks
    </template>
  </EmptyStateBox>
</template>
<script setup lang="ts">
import { h, ref, computed } from 'vue'
import { Dropdown, LoadingIndicator, Tooltip, dayjsLocal } from 'frappe-ui'
import EmptyStateBox from './EmptyStateBox.vue'
import TaskStatusIcon from './NewTaskDialog/TaskStatusIcon.vue'
import { useList } from 'frappe-ui/src/data-fetching'
import { GPTask } from '@/types/doctypes'
import { UseListOptions } from 'frappe-ui/src/data-fetching/useList/types'
import DropdownMoreOptions from './DropdownMoreOptions.vue'
import { createDialog } from '@/utils/dialogs'

interface Props {
  groupByStatus?: boolean
  listOptions?: {
    filters?: UseListOptions<GPTask>['filters']
    orderBy?: UseListOptions<GPTask>['orderBy']
    pageLength?: UseListOptions<GPTask>['limit']
  }
}

const props = withDefaults(defineProps<Props>(), {
  groupByStatus: false,
  listOptions: () => ({
    orderBy: 'creation desc',
    pageLength: 20,
  }),
})

type TaskStatus = GPTask['status']
let statues: Array<TaskStatus> = ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled']

const isOpen = ref<Record<TaskStatus, boolean>>({
  Backlog: true,
  Todo: true,
  'In Progress': true,
  Canceled: false,
  Done: false,
})

const tasks = useList<GPTask>({
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_task.gp_task.get_list',
  doctype: 'GP Task',
  fields: ['*', 'project.title as project_title'],
  filters: props.listOptions.filters,
  orderBy: props.listOptions.orderBy,
  limit: props.listOptions.pageLength,
  cacheKey: ['Tasks', props.listOptions],
})

const tasksByStatus = computed(() => {
  const grouped: Record<TaskStatus, GPTask[]> = {
    Backlog: [],
    Todo: [],
    'In Progress': [],
    Done: [],
    Canceled: [],
  }
  for (let task of tasks.data || []) {
    if (!task.status) {
      task.status = 'Backlog'
    }
    if (!grouped[task.status]) {
      grouped[task.status] = []
    }
    grouped[task.status].push(task)
  }
  return grouped
})

const groupedTasks = computed(() => {
  if (!props.groupByStatus) {
    return [
      {
        id: 'all',
        title: '',
        tasks: tasks.data || [],
      },
    ]
  }

  return (['In Progress', 'Todo', 'Backlog', 'Done', 'Canceled'] as Array<TaskStatus>).map(
    (status) => ({
      id: status,
      title: status,
      tasks: tasksByStatus.value[status] || [],
    }),
  )
})

function dropdownOptions(name: string) {
  return [
    {
      label: 'Delete',
      onClick: () => {
        createDialog({
          title: 'Delete Task',
          message: 'Are you sure you want to delete this task?',
          actions: [
            {
              label: 'Delete',
              onClick: ({ close }) => {
                return tasks.delete.submit({ name }).then(close)
              },
            },
          ],
        })
      },
    },
  ]
}

function statusOptions({ onClick }: { onClick: (status: GPTask['status']) => void }) {
  return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map((status) => ({
    icon: () => h(TaskStatusIcon, { status }),
    label: status,
    onClick: () => onClick(status as GPTask['status']),
  }))
}

defineExpose({ tasks })
</script>
