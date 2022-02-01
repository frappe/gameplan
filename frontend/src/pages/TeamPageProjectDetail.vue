<template>
  <div class="pb-40" v-if="$resources.project.data">
    <div class="container py-8 mx-auto">
      <div>
        <h1 class="text-6xl font-bold">
          {{ project.title }}
        </h1>
        <p class="text-sm text-gray-500">
          created {{ $dayjs(project.creation).fromNow() }}
          {{ $resources.updateProject.loading ? 'saving...' : '' }}
        </p>
      </div>
    </div>
    <div class="border-b">
      <div
        class="container flex py-2 mx-auto text-sm font-medium text-gray-500"
      >
        <div class="w-[70%]">Task</div>
        <div class="w-[15%]">Assignee</div>
        <div class="w-[15%]">Due Date</div>
      </div>
    </div>
    <div class="mb-4" v-for="state in project.task_states" :key="state.status">
      <div
        class="container flex py-2 mx-auto text-lg font-semibold text-gray-900"
      >
        <button class="p-1 mr-1 transition-colors rounded hover:bg-gray-100">
          <FeatherIcon name="chevron-right" class="w-4 h-4" />
        </button>
        <div>{{ state.status }}</div>
      </div>
      <div class="container" v-for="task in tasksByStatus(state.status)">
        <div
          class="mx-auto text-base font-medium text-gray-700 border-t hover:bg-gray-50"
        >
          <div class="flex">
            <div class="flex pl-8 py-2 w-[70%]">
              <button class="block mr-2">
                <FeatherIcon
                  name="circle"
                  class="w-4 text-gray-400 transition-colors hover:text-gray-600"
                />
              </button>
              {{ task.title }}
            </div>
            <div class="w-[15%] flex flex-shrink-0">
              <AssignUser
                class="w-full h-full"
                :users="users"
                :assigned-user="task.assignedUser"
                @update:assigned-user="updateAssignedUser(task, $event)"
              />
            </div>
            <div class="w-[15%] flex-shrink-0"></div>
          </div>
        </div>
      </div>
      <div class="container">
        <div class="mx-auto text-sm font-medium text-gray-700 border-t">
          <div class="flex pl-8">
            <button class="block mr-2">
              <Spinner
                class="w-4"
                v-if="
                  $resources.createTask.loading &&
                  $resources.createTask.params.doc.status === state.status
                "
              />
              <FeatherIcon
                v-else
                name="circle"
                class="w-4 text-gray-400 transition-colors hover:text-gray-600"
              />
            </button>
            <div class="w-[70%]">
              <input
                :ref="(ref) => setNewTaskRef(ref, state.status)"
                class="w-full p-0 py-2 text-base font-medium text-gray-700 border-none focus:ring-0"
                type="text"
                @keydown.enter="
                  $resources.createTask.submit({
                    doc: {
                      doctype: 'Team Task',
                      project: projectId,
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
    <div class="container mx-auto mt-4">
      <Button
        v-show="!addingNewStatus"
        icon-left="plus"
        type="white"
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
  </div>
</template>
<script>
import { Spinner, debounce } from 'frappe-ui'
import AssignUser from '@/components/AssignUser.vue'

export default {
  name: 'TeamPageProjectDetail',
  props: ['team', 'projectId'],
  components: {
    Spinner,
    AssignUser,
  },
  data() {
    return {
      addingNewStatus: false,
      newStatus: '',
    }
  },
  resources: {
    project() {
      return {
        method: 'frappe.client.get',
        cache: ['team-project', this.projectId],
        params: {
          doctype: 'Team Project',
          name: this.projectId,
        },
        auto: true,
      }
    },
    tasks() {
      return {
        method: 'frappe.client.get_list',
        cache: ['team-project-tasks', this.projectId],
        params: {
          doctype: 'Team Task',
          filters: {
            project: this.projectId,
          },
          fields: ['*'],
          order_by: 'creation asc',
        },
        auto: Boolean(this.project),
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
    updateProject() {
      return {
        method: 'frappe.client.set_value',
        params: {
          doctype: 'Team Project',
          name: this.projectId,
          fieldname: {
            description: this.project?.description,
          },
        },
      }
    },
    createTask() {
      return {
        method: 'frappe.client.insert',
        async onSuccess(data) {
          await this.$resources.tasks.fetch()
          await this.$nextTick()
          let input = this.newTaskRefs[data.status]
          if (input) {
            input.value = ''
            input.focus()
          }
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
          name: this.projectId,
          fieldname: {
            task_states,
          },
        },
        onSuccess() {
          this.newStatus = ''
          this.addingNewStatus = false
          this.$resources.project.fetch()
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
  },
  computed: {
    project() {
      return this.$resources.project.data
    },
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
    onDescriptionUpdate(content) {
      this.$resources.project.data.description = content
      this.updateProject()
    },
    updateProject: debounce(function () {
      this.$resources.updateProject.submit()
    }, 700),
  },
}
</script>
