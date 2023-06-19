<template>
  <div class="flex">
    <div class="h-full w-full py-6">
      <div class="mb-4.5 flex items-center justify-between">
        <h2 class="text-xl font-semibold text-gray-900">Tasks</h2>
        <div class="flex items-stretch space-x-2">
          <Select
            :options="[
              { label: 'All', value: 'all' },
              { label: 'Active', value: 'active' },
              { label: 'Backlog', value: 'backlog' },
              { label: 'Done', value: 'done' },
              { label: 'Canceled', value: 'canceled' },
            ]"
            v-model="_listType"
          />
          <Button
            variant="solid"
            @click="showNewTaskDialog"
            v-if="!$readOnlyMode && !project.doc.archived_at"
          >
            <template #prefix>
              <FeatherIcon class="h-4 w-4" name="plus" />
            </template>
            Add new
          </Button>
        </div>
      </div>
      <div>
        <div v-for="d in $resources.tasks.data" :key="d.name">
          <router-link
            :to="{
              name: 'ProjectTaskDetail',
              params: { teamId: d.team, projectId: d.project, taskId: d.name },
            }"
            class="-mx-2.5 flex items-center rounded p-2.5 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
            :class="{
              'pointer-events-none':
                $resources.tasks.delete.loading &&
                $resources.tasks.delete.params.name === d.name,
            }"
          >
            <div>
              <div class="flex items-start">
                <LoadingIndicator
                  class="h-4 w-4 text-gray-600"
                  v-if="
                    $resources.tasks.delete.loading &&
                    $resources.tasks.delete.params.name === d.name
                  "
                />
                <Tooltip text="Change status" v-else>
                  <Dropdown
                    :options="
                      statusOptions({
                        onClick: (status) =>
                          $resources.tasks.setValue.submit({
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
                <span
                  class="ml-2.5 text-base font-medium leading-4 text-gray-900"
                >
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
                    <FeatherIcon
                      name="calendar"
                      class="h-3 w-3 text-gray-700"
                    />
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

            <Dropdown
              class="ml-auto"
              placement="right"
              :button="{
                icon: 'more-horizontal',
                variant: 'ghost',
              }"
              :options="[
                {
                  label: 'Delete',
                  icon: 'trash',
                  onClick: () => {
                    this.$resources.tasks.delete.submit(d.name)
                  },
                },
              ]"
            />
          </router-link>
          <div class="w-full border-b"></div>
        </div>
      </div>
      <div
        class="flex items-center justify-center p-3"
        v-if="$resources.tasks.hasNextPage"
      >
        <Button
          @click="$resources.tasks.next"
          :loading="$resources.tasks.list.loading"
        >
          <template #prefix>
            <LucideRefreshCw class="h-4 w-4" />
          </template>
          {{ $resources.tasks.loading ? 'Loading...' : 'Load more' }}
        </Button>
      </div>
      <div
        class="text-base text-gray-600"
        v-if="!$resources.tasks.loading && !$resources.tasks.data?.length"
      >
        No tasks
      </div>
    </div>
    <NewTaskDialog ref="newTaskDialog" />
  </div>
</template>
<script>
import { h } from 'vue'
import {
  Avatar,
  Popover,
  Tooltip,
  Dropdown,
  Select,
  Dialog,
  FormControl,
  Autocomplete,
  TextInput,
  LoadingIndicator,
} from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import TaskStatusIcon from '@/components/icons/TaskStatusIcon.vue'

export default {
  name: 'ProjectTasks',
  props: ['project', 'listType'],
  resources: {
    tasks() {
      let filters = {
        project: this.project.doc.name,
      }
      if (this.listType === 'all') {
        // pass
      }
      if (this.listType === 'active') {
        filters.status = ['in', ['Todo', 'In Progress']]
      }
      if (this.listType === 'backlog') {
        filters.status = 'Backlog'
      }
      if (this.listType === 'done') {
        filters.status = 'Done'
      }
      if (this.listType === 'canceled') {
        filters.status = 'Canceled'
      }
      return {
        type: 'list',
        url: 'gameplan.gameplan.doctype.gp_task.gp_task.get_list',
        cache: ['Project Tasks', this.project.doc.name, this.listType],
        doctype: 'GP Task',
        fields: ['*'],
        filters,
        orderBy: 'creation desc',
        auto: true,
        realtime: true,
      }
    },
  },
  methods: {
    showNewTaskDialog() {
      let status = 'Backlog'
      if (this.listType === 'active') {
        status = 'Todo'
      } else if (this.listType === 'done') {
        status = 'Done'
      }

      this.$refs.newTaskDialog.show({
        defaults: {
          status,
          assigned_to: this.$user().name,
          project: this.project.name,
        },
        onSuccess: () => {
          this.$resources.tasks.reload()
        },
      })
    },
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
    _listType: {
      get() {
        return this.listType
      },
      set(value) {
        this.$router.replace({
          name: 'ProjectTasks',
          params: {
            teamId: this.project.doc.team,
            projectId: this.project.doc.name,
            listType: value,
          },
        })
      },
    },
  },
  components: {
    Avatar,
    Popover,
    UserAvatar,
    Dropdown,
    TaskStatusIcon,
    Tooltip,
    Select,
    Dialog,
    FormControl,
    Autocomplete,
    TextInput,
    LoadingIndicator,
  },
}
</script>
