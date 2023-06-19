<template>
  <div class="@container" v-if="tasks.data?.length">
    <div v-for="(d, index) in tasks.data" :key="d.name">
      <router-link
        :to="{
          name: d.project ? 'ProjectTaskDetail' : 'HomeTask',
          params: { teamId: d.team, projectId: d.project, taskId: d.name },
        }"
        class="flex h-15 w-full items-center rounded p-2.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
        :class="{
          'pointer-events-none':
            tasks.delete.loading && tasks.delete.params.name === d.name,
        }"
      >
        <div class="w-full">
          <div class="flex min-w-0 items-start">
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
            <div
              class="ml-2.5 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium leading-4 text-gray-900"
            >
              {{ d.title }}
            </div>
            <div
              class="ml-auto shrink-0 whitespace-nowrap text-sm text-gray-600"
            >
              {{ $dayjs(d.modified).fromNow() }}
            </div>
          </div>

          <div class="ml-6.5 mt-1.5 flex items-center">
            <div class="text-base text-gray-600">#{{ d.name }}</div>
            <div
              v-if="d.project"
              class="flex items-center text-base leading-none text-gray-700"
            >
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              {{ d.team_title }}
              <LucideChevronRight class="h-3 w-3 text-gray-600" />
              {{ d.project_title }}
            </div>
            <div class="flex items-center">
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              <UserAvatar size="xs" :user="d.assigned_to" />
              <span
                class="ml-2 hidden whitespace-nowrap text-base text-gray-800 @md:inline"
              >
                {{ $user(d.assigned_to).full_name }}
              </span>
            </div>

            <template v-if="d.due_date">
              <div class="px-2 leading-none text-gray-600">&middot;</div>
              <div class="flex items-center">
                <LucideCalendar class="h-3 w-3 text-gray-700" />
                <span class="ml-2 whitespace-nowrap text-base text-gray-700">
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
            <div
              class="ml-auto inline-grid h-4 w-4 shrink-0 place-items-center rounded-full bg-gray-200 text-xs"
              :class="[
                d.unread ? 'text-gray-900' : 'text-gray-600',
                d.comments_count ? '' : 'invisible',
              ]"
            >
              {{ d.comments_count || 0 }}
            </div>
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
<script>
import { h } from 'vue'
import { LoadingIndicator, Dropdown, Tooltip } from 'frappe-ui'
import TaskStatusIcon from './icons/TaskStatusIcon.vue'

export default {
  name: 'TaskList',
  props: {
    listOptions: {
      type: Object,
      default: () => ({}),
    },
  },
  components: {
    LoadingIndicator,
    Dropdown,
    Tooltip,
    TaskStatusIcon,
  },
  resources: {
    tasks() {
      return {
        type: 'list',
        cache: ['Tasks', this.listOptions],
        doctype: 'GP Task',
        fields: [
          '*',
          'project.title as project_title',
          'team.title as team_title',
        ],
        filters: this.listOptions.filters,
        orderBy: this.listOptions.orderBy || 'creation desc',
        pageLength: this.listOptions.pageLength || 20,
        auto: true,
        realtime: true,
      }
    },
  },
  methods: {
    statusOptions({ onClick }) {
      return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map(
        (status) => {
          return {
            icon: () => h(TaskStatusIcon, { status }),
            label: status,
            onClick: () => onClick(status),
          }
        }
      )
    },
  },
  computed: {
    tasks() {
      return this.$resources.tasks
    },
  },
}
</script>
