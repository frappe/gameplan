<template>
  <template v-if="!$resources.tasks.data">
    <div
      class="container flex items-center py-2 mx-auto text-lg font-semibold text-gray-900"
    >
      <Button
        class="mr-1"
        appearance="minimal"
        :icon="'chevron-down'"
        :disabled="true"
      />
      <div>Loading...</div>
    </div>
    <div class="container">
      <div class="mx-auto text-sm font-medium text-gray-700 border-t">
        <div class="flex pl-8">
          <button class="block mr-2" disabled>
            <FeatherIcon
              name="circle"
              class="w-4 text-gray-300 animate-pulse"
            />
          </button>
          <div class="w-[70%] py-2">
            <div class="w-40 py-2 bg-gray-100 rounded animate-pulse"></div>
          </div>
          <div class="w-[15%]"></div>
          <div class="w-[10%]"></div>
        </div>
      </div>
    </div>
  </template>
  <div v-for="state in $resources.tasks.data" :key="state.status">
    <div class="container flex items-center py-2 mx-auto">
      <Button
        class="mr-1"
        appearance="minimal"
        @click="state.open = !state.open"
        :icon="state.open ? 'chevron-down' : 'chevron-right'"
      />
      <div class="text-lg font-semibold text-gray-900">{{ state.status }}</div>
      <Dropdown
        placement="left"
        class="ml-1"
        :button="{
          icon: 'more-horizontal',
          appearance: 'minimal',
        }"
        :options="[
          {
            label: 'Move tasks to another group',
            icon: 'log-out',
            handler: () => {
              changeGroupDialog.show = true
              changeGroupDialog.fromGroup = state.status
            },
          },
          {
            label: 'Delete',
            icon: 'trash-2',
            handler: () => {
              deleteGroupDialog.show = true
              deleteGroupDialog.group = state.status
            },
          },
        ]"
      />
    </div>
    <div v-if="state.open">
      <template v-if="state.tasks">
        <Draggable
          v-model="state.tasks"
          group="tasks"
          item-key="name"
          @sort="updateTasks(state, state.status)"
        >
          <template #item="{ element: task }">
            <div class="container" v-show="!task.deleted">
              <div class="mx-auto border-t hover:bg-gray-50 group">
                <div class="flex">
                  <div class="flex items-center pl-1.5 w-[70%]">
                    <button class="mr-2 opacity-0 group-hover:opacity-100">
                      <DragHandleIcon class="w-4 h-4 text-gray-400" />
                    </button>
                    <button
                      class="block mr-2"
                      @click="
                        $resources.updateTaskField.submit({
                          task: task.name,
                          is_completed: !Boolean(task.is_completed),
                        })
                      "
                      :disabled="$resources.updateTaskField.loading"
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
                          'text-gray-500 hover:text-gray-700':
                            task.is_completed,
                          'text-gray-400 hover:text-gray-600':
                            !task.is_completed,
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
                      class="w-full h-full text-sm text-gray-700"
                      :class="
                        task.assignedUser
                          ? ''
                          : 'opacity-0 group-hover:opacity-100'
                      "
                      :users="users"
                      :assignedUser="task.assignedUser"
                      @update:assigned-user="updateAssignedUser(task, $event)"
                    />
                  </div>
                  <div class="w-[10%] flex-shrink-0">
                    <input
                      type="date"
                      class="w-full h-full p-0 text-sm bg-transparent border-none focus:outline-none"
                      :class="
                        task.due_date
                          ? 'text-gray-700'
                          : 'text-gray-500 opacity-0 group-hover:opacity-100'
                      "
                      :value="(task.due_date || '').split(' ')[0]"
                      @change="
                        (e) => {
                          task.due_date = e.target.value
                          $resources.updateTaskField.submit({
                            task: task.name,
                            due_date: task.due_date,
                          })
                        }
                      "
                    />
                  </div>
                  <div
                    class="w-[5%] flex items-center justify-end flex-shrink-0 opacity-0 group-hover:opacity-100"
                  >
                    <Dropdown
                      :button="{
                        icon: 'more-horizontal',
                        appearance: 'minimal',
                      }"
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
        </Draggable>
      </template>
      <div class="container mb-4">
        <div class="mx-auto text-sm font-medium text-gray-700 border-t">
          <div class="flex pl-7">
            <div class="w-0.5"></div>
            <button class="block mr-2">
              <FeatherIcon
                name="circle"
                class="w-4 text-gray-400 transition-colors hover:text-gray-600"
              />
            </button>
            <div class="w-[70%]">
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
  <Dialog
    :options="{
      title: `Move tasks from ${changeGroupDialog.fromGroup}`,
      actions: [
        {
          label: changeGroupDialog.toGroup
            ? `Move tasks to ${changeGroupDialog.toGroup}`
            : 'Move tasks',
          appearance: 'primary',
          loading: $resources.bulkUpdateTasks.loading,
          handler: () => changeGroup(),
        },
      ],
    }"
    v-model="changeGroupDialog.show"
  >
    <template #body-content>
      <Input
        type="select"
        :options="[
          '',
          ...project.task_states
            .map((t) => t.status)
            .filter((t) => t !== changeGroupDialog.fromGroup),
        ]"
        label="Select Group"
        v-model="changeGroupDialog.toGroup"
      />
    </template>
  </Dialog>
  <Dialog
    :options="{
      title: 'Delete Group',
      icon: {
        name: 'trash-2',
        appearance: 'danger',
      },
      message: `Are you sure you want to delete the group: ${deleteGroupDialog.group}?`,
      actions: [
        {
          label: 'Delete',
          appearance: 'danger',
          loading: $resources.deleteGroup.loading,
          handler: () => $resources.deleteGroup.submit(),
        },
      ],
    }"
    v-model="deleteGroupDialog.show"
    @update:modelValue="
      (val) => {
        if (!val) {
          deleteGroupDialog.group = ''
          $resources.deleteGroup.reset()
        }
      }
    "
  >
    <template #body-content>
      <p class="text-sm text-gray-600">
        Are you sure you want to delete the group:
        {{ deleteGroupDialog.group }}?
      </p>
      <ErrorMessage
        class="mt-2"
        :message="$resources.deleteGroup.error?.messages"
      />
    </template>
  </Dialog>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import Draggable from 'vuedraggable'
import AssignUser from '@/components/AssignUser.vue'
import DragHandleIcon from '@/components/DragHandleIcon.vue'

export default {
  name: 'ProjectDetailTasks',
  props: ['project'],
  components: {
    Dropdown,
    Spinner,
    AssignUser,
    Draggable,
    DragHandleIcon,
  },
  data() {
    return {
      addingNewStatus: false,
      changeGroupDialog: { fromGroup: null, toGroup: null, show: false },
      deleteGroupDialog: { group: null, show: false },
      newStatus: '',
    }
  },
  resources: {
    tasks() {
      return {
        method: 'teams.api.project_tasks',
        cache: ['team-project-tasks', this.project.name],
        params: {
          project: this.project.name,
        },
        auto: Boolean(this.project),
        debounce: 300,
        onSuccess(states) {
          for (let state of states) {
            state.open = true
            state.tasks.forEach((task, i) => {
              if (!task.idx) {
                task.idx = i + 1
              }
              let assignedUserEmail = task._assign
                ? JSON.parse(task._assign)[0]
                : null
              task.assignedUser = assignedUserEmail
                ? this.users.find((user) => user.email === assignedUserEmail)
                : null
            })
          }
        },
      }
    },
    createTask() {
      return {
        method: 'frappe.client.insert',
        onFetch(params) {
          // optimistic update
          for (let state of this.$resources.tasks.data) {
            if (state.status == params.doc.status) {
              params.doc.idx = state.tasks.length + 1
              state.tasks.push(params.doc)
            }
          }
          let input = this.newTaskRefs[params.doc.status]
          if (input) {
            input.value = ''
            this.$nextTick(() => input.focus())
          }
        },
        onSuccess() {
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
          this.$resources.tasks.reload()
          this.$refetchResource(['Team Project', this.project.name])
        },
      }
    },
    deleteGroup() {
      return {
        method: 'teams.api.delete_group',
        params: {
          project: this.project.name,
          group: this.deleteGroupDialog.group,
        },
        onSuccess() {
          this.deleteGroupDialog.show = false
          this.deleteGroupDialog.group = null
          this.$resources.tasks.reload()
          this.$refetchResource(['Team Project', this.project.name])
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
    updateTaskField() {
      return {
        method: 'frappe.client.set_value',
        makeParams(args) {
          let { task, ...fields } = args
          return {
            doctype: 'Team Task',
            name: task,
            fieldname: fields,
          }
        },
        onFetch(params) {
          // optimistic update
          if (params.name) {
            let task = this.tasks.find((task) => task.name === params.name)
            task.is_completed = params.fieldname.is_completed
          }
        },
        onSuccess(task) {
          this.$refetchResource(['Team Project'])
          this.$resources.tasks.data = this.$resources.tasks.data.map((t) => {
            if (t.name === task.name) {
              Object.assign(t, task)
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
          for (let task of this.tasks) {
            if (task.name === params.name) {
              task.deleted = true
            }
          }
        },
        onSuccess() {
          this.$refetchResource(['Team Project'])
          this.$resources.tasks.fetch()
        },
        onError() {
          this.$resources.tasks.fetch()
        },
      }
    },
    bulkUpdateTasks() {
      return {
        method: 'frappe.client.bulk_update',
        onSuccess() {
          this.changeGroupDialog.show = false
          this.$resources.tasks.fetch()
        },
      }
    },
    deleteState() {
      return {
        method: 'frappe.client.set_value',
      }
    },
  },
  computed: {
    tasks() {
      let states = this.$resources.tasks.data || []
      let tasks = []
      for (let state of states) {
        tasks = tasks.concat(state.tasks)
      }
      return tasks
    },
    users() {
      return this.project?.members || []
    },
  },
  methods: {
    log: console.log,
    updateTasks(state, status) {
      state.tasks.forEach((task, i) => {
        task.idx = i + 1
        task.status = status
      })

      this.$resources.bulkUpdateTasks.submit({
        docs: JSON.stringify(
          state.tasks.map((task) => ({
            doctype: 'Team Task',
            docname: task.name,
            status: task.status,
            idx: task.idx,
          }))
        ),
      })
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
    deleteState(state) {
      this.$resources.deleteState.submit({
        project: this.project.name,
        status: state.status,
      })
    },
    changeGroup() {
      for (let d of this.$resources.tasks.data) {
        if (d.status === this.changeGroupDialog.fromGroup) {
          this.$resources.bulkUpdateTasks.submit({
            docs: JSON.stringify(
              d.tasks.map((t) => ({
                doctype: 'Team Task',
                docname: t.name,
                status: this.changeGroupDialog.toGroup,
              }))
            ),
          })
          this.changeGroupDialog.fromGroup = null
          this.changeGroupDialog.toGroup = null
        }
      }
    },
  },
}
</script>
