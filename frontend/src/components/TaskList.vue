<template>
  <div v-if="tasks.data?.length">
    <div v-for="(d, index) in tasks.data" :key="d.name">
      <router-link
        :to="{
          name: 'ProjectTaskDetail',
          params: { teamId: d.team, projectId: d.project, taskId: d.name },
        }"
        class="flex h-15 items-center rounded p-2.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
        :class="{
          'pointer-events-none':
            tasks.delete.loading && tasks.delete.params.name === d.name,
        }"
      >
        <div>
          <div class="flex items-start">
            <LoadingIndicator
              class="h-4 w-4 text-gray-600"
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
                  class="flex rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                >
                  <TaskStatusIcon :status="d.status" />
                </button>
              </Dropdown>
            </Tooltip>
            <span class="ml-2.5 text-base font-medium leading-4 text-gray-900">
              {{ d.title }}
            </span>
          </div>

          <div class="ml-6.5 mt-1.5 flex items-center">
            <div class="text-base text-gray-600">#{{ d.name }}</div>
            <div class="flex items-center">
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              <UserAvatar class="mr-2" size="xs" :user="d.assigned_to" />
              <span class="text-base text-gray-800">
                {{ $user(d.assigned_to).full_name }}
              </span>
            </div>

            <template v-if="d.due_date">
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              <div class="flex items-center">
                <LucideCalendar class="h-3 w-3 text-gray-700" />
                <span class="ml-2 text-base text-gray-700">
                  {{ $dayjs(d.due_date).format('D MMM') }}</span
                >
              </div>
            </template>
            <template v-if="d.priority">
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              <div class="flex items-center">
                <span class="text-base text-gray-700">
                  {{ d.priority }}
                </span>
              </div>
            </template>
          </div>
        </div>
      </router-link>
      <div class="mx-2.5 border-b" v-if="index < tasks.data.length - 1"></div>
    </div>
  </div>
  <div
    class="flex flex-col items-center rounded-lg border-2 border-dashed py-8 text-base text-gray-600"
    v-else
  >
    No tasks
  </div>
</template>
<script setup>
import { h } from 'vue'
import {
  LoadingIndicator,
  Dropdown,
  Tooltip,
  createListResource,
} from 'frappe-ui'
import TaskStatusIcon from './icons/TaskStatusIcon.vue'

const props = defineProps({
  listOptions: {
    type: Object,
    default: () => ({}),
  },
})

const tasks = createListResource({
  type: 'list',
  cache: ['Tasks', props.listOptions],
  doctype: 'GP Task',
  fields: ['*'],
  filters: props.listOptions.filters,
  orderBy: props.listOptions.orderBy || 'creation desc',
  pageLength: props.listOptions.pageLength || 20,
  auto: true,
  realtime: true,
})

const statusOptions = ({ onClick }) => {
  return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map(
    (status) => {
      return {
        icon: () => h(TaskStatusIcon, { status }),
        label: status,
        onClick: () => onClick(status),
      }
    }
  )
}
</script>