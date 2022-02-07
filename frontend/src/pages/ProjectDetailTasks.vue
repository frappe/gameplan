<template>
  <div class="border-b">
    <div class="container flex py-2 mx-auto text-sm font-medium text-gray-500">
      <div class="w-[65%]">Task</div>
      <div class="w-[15%]">Assignee</div>
      <div class="w-[15%]">Due Date</div>
      <div class="w-[5%]"></div>
    </div>
  </div>
  <div v-for="state in project.task_states" :key="state.status">
    <div
      class="container flex items-center py-2 mx-auto text-lg font-semibold text-gray-900"
    >
      <Button
        class="mr-1"
        appearance="minimal"
        @click="state.open = !state.open"
        :icon="state.open ? 'chevron-down' : 'chevron-right'"
      />
      <div>{{ state.status }}</div>
    </div>
    <div v-if="state.open">
      <template v-if="$resources.tasks.data">
        <div
          class="container"
          v-for="task in tasksByStatus(state.status)"
          :key="task.name"
          :animate="{ opacity: 1 }"
        >
          <div class="mx-auto border-t hover:bg-gray-50 group">
            <div class="flex">
              <div class="flex pl-8 w-[65%]">
                <button
                  class="block mr-2"
                  @click="
                    $resources.updateTaskCompleted.submit({
                      doctype: 'Team Task',
                      name: task.name,
                      fieldname: {
                        is_completed: !Boolean(task.is_completed),
                      },
                    })
                  "
                  :disabled="$resources.updateTaskCompleted.loading"
                  :aria-label="
                    task.is_completed
                      ? 'Mark as incomplete'
                      : 'Mark as complete'
                  "
                >
                  <FeatherIcon
                    :name="task.is_completed ? 'check' : 'circle'"
                    class="w-4 transition-colors"
                    :class="{
                      'text-gray-500 hover:text-gray-700': task.is_completed,
                      'text-gray-400 hover:text-gray-600': !task.is_completed,
                    }"
                  />
                </button>
                <input
                  :class="[
                    'text-base font-medium w-full p-1 bg-transparent transition-colors border-none focus:ring-0',
                    task.is_completed
                      ? 'line-through text-gray-500'
                      : 'text-gray-800',
                  ]"
                  type="text"
                  v-model="task.title"
                  @input="
                    () => {
                      if (!task.title) return
                      $resources.updateTaskTitle.submit({
                        doctype: 'Team Task',
                        name: task.name,
                        fieldname: {
                          title: task.title,
                        },
                      })
                    }
                  "
                  @blur="
                    () => {
                      if (task.title) return
                      $resources.deleteTask.submit({
                        doctype: 'Team Task',
                        name: task.name,
                      })
                    }
                  "
                />
              </div>
              <div class="w-[15%] flex flex-shrink-0">
                <AssignUser
                  class="w-full h-full opacity-0 group-hover:opacity-100"
                  :users="users"
                  :assignedUser="task.assignedUser"
                  @update:assigned-user="updateAssignedUser(task, $event)"
                />
              </div>
              <div class="w-[15%] flex-shrink-0"></div>
              <div
                class="w-[5%] flex items-center justify-end flex-shrink-0 opacity-0 group-hover:opacity-100"
              >
                <Dropdown
                  :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
                  :options="[
                    {
                      label: 'Delete',
                      icon: 'trash-2',
                      handler: () => {
                        $resources.deleteTask.submit({
                          doctype: 'Team Task',
                          name: task.name,
                        })
                      },
                    },
                  ]"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
      <div class="container" v-else>
        <div class="mx-auto text-sm font-medium text-gray-700 border-t">
          <div class="flex pl-8">
            <button class="block mr-2">
              <FeatherIcon
                name="circle"
                class="w-4 text-gray-300 animate-pulse"
              />
            </button>
            <div class="w-[65%] py-2">
              <div class="w-40 py-2 bg-gray-100 rounded animate-pulse"></div>
            </div>
            <div class="w-[15%]"></div>
            <div class="w-[15%]"></div>
          </div>
        </div>
      </div>
      <div class="container mb-4">
        <div class="mx-auto text-sm font-medium text-gray-700 border-t">
          <div class="flex pl-8">
            <button class="block mr-2">
              <FeatherIcon
                name="circle"
                class="w-4 text-gray-400 transition-colors hover:text-gray-600"
              />
            </button>
            <div class="w-[65%]">
              <input
                :ref="(ref) => setNewTaskRef(ref, state.status)"
                class="w-full p-1 text-base font-medium text-gray-700 border-none focus:ring-0"
                type="text"
                @keydown.enter="
                  $resources.createTask.submit({
                    doc: {
                      doctype: 'Team Task',
                      project: project.name,
                      title: newTaskRefs[state.status].value,
                      status: state.status,
                    },
                  })
                "
                placeholder="Add a task"
                :disabled="$resources.createTask.loading"
              />
            </div>
            <div class="w-[15%]"></div>
            <div class="w-[15%]"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="container mx-auto mt-4">
    <Button
      v-show="!addingNewStatus"
      icon-left="plus"
      appearance="white"
      @click="
        () => {
          addingNewStatus = true
          $nextTick(() => $refs.newStatusInput.focus())
        }
      "
    >
      Add status
    </Button>
    <div class="flex items-center" v-if="addingNewStatus">
      <button class="p-1 mr-1 transition-colors rounded hover:bg-gray-100">
        <Spinner class="w-4" v-if="$resources.createStatus.loading" />
        <FeatherIcon name="chevron-right" class="w-4 h-4" v-else />
      </button>
      <input
        ref="newStatusInput"
        type="text"
        class="p-0 text-lg font-semibold text-gray-900 border-none focus:ring-0"
        v-model="newStatus"
        @keydown.enter="$resources.createStatus.submit()"
        :disabled="$resources.createStatus.loading"
      />
    </div>
  </div>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import AssignUser from '@/components/AssignUser.vue'

export default {
  name: 'ProjectDetailTasks',
  props: ['project'],
  components: { Dropdown, Spinner, AssignUser },
  data() {
    return {
      addingNewStatus: false,
      newStatus: '',
    }
  },
  resources: {
    tasks() {
      return {
        method: 'frappe.client.get_list',
        cache: ['team-project-tasks', this.project.name],
        params: {
          doctype: 'Team Task',
          filters: {
            project: this.project.name,
          },
          fields: ['*'],
          order_by: 'creation asc',
          limit_page_length: 100,
        },
        auto: Boolean(this.project),
        debounce: 300,
        onSuccess(tasks) {
          for (let task of tasks) {
            let assignedUserEmail = task._assign
              ? JSON.parse(task._assign)[0]
              : null
            task.assignedUser = assignedUserEmail
              ? this.users.find((user) => user.email === assignedUserEmail)
              : null
          }
        },
      }
    },
    createTask() {
      return {
        method: 'frappe.client.insert',
        onFetch(params) {
          // optimistic update
          this.$resources.tasks.data.push(params.doc)
          let input = this.newTaskRefs[params.doc.status]
          if (input) {
            input.value = ''
            this.$nextTick(() => input.focus())
          }
        },
        onSuccess(data) {
          this.$resources.tasks.fetch()
        },
      }
    },
    createStatus() {
      let task_states = [
        ...(this.project?.task_states || []),
        {
          status: this.newStatus,
        },
      ]
      return {
        method: 'frappe.client.set_value',
        params: {
          doctype: 'Team Project',
          name: this.project.name,
          fieldname: {
            task_states,
          },
        },
        onSuccess() {
          this.newStatus = ''
          this.addingNewStatus = false
          this.$refetchResource(['team-project', this.project.name])
        },
      }
    },
    assignTask() {
      return {
        method: 'teams.api.assign_task',
        onSuccess() {
          this.$resources.tasks.fetch()
        },
      }
    },
    updateTaskCompleted() {
      return {
        method: 'frappe.client.set_value',
        onFetch(params) {
          // optimistic update
          if (params.task) {
            let task = this.tasks.find((task) => task.name === params.task)
            task.is_completed = params.fieldname.is_completed
          }
        },
        onSuccess(task) {
          this.$refetchResource(['team-project'])
          this.$resources.tasks.data = this.$resources.tasks.data.map((t) => {
            if (t.name === task.name) {
              return task
            }
            return t
          })
        },
      }
    },
    updateTaskTitle() {
      return {
        method: 'frappe.client.set_value',
        debounce: 500,
      }
    },
    deleteTask() {
      return {
        method: 'frappe.client.delete',
        onFetch(params) {
          // optimistic update
          this.$resources.tasks.data = this.tasks.filter(
            (task) => task.name !== params.name
          )
        },
        onSuccess() {
          this.$refetchResource(['team-project'])
          this.$resources.tasks.fetch()
        },
        onError() {
          this.$resources.tasks.fetch()
        },
      }
    },
  },
  computed: {
    tasks() {
      return this.$resources.tasks.data || []
    },
    users() {
      return this.project?.members || []
    },
  },
  methods: {
    tasksByStatus(status) {
      return this.tasks.filter((task) => task.status === status)
    },
    setNewTaskRef(ref, status) {
      this.newTaskRefs = this.newTaskRefs || {}
      this.newTaskRefs[status] = ref
    },
    updateAssignedUser(task, user) {
      task.assignedUser = user
      this.$resources.assignTask.submit({
        task: task.name,
        user: user.email,
      })
    },
  },
}
</script>
