<template>
  <div class="flex flex-col" v-if="task && task.doc">
    <div class="py-5">
      <div class="flex items-start justify-between">
        <input
          v-if="editTaskTitle"
          type="text"
          class="-ml-1 w-full rounded-md border-none p-1 text-2xl font-semibold focus:bg-gray-100 focus:outline-none focus:ring-0"
          :class="{ 'bg-gray-100': editTaskTitle }"
          v-model="task.doc.title"
          ref="taskTitle"
          :disabled="!editTaskTitle"
          @keydown.enter="updateTaskTitle()"
          v-focus
        />
        <h1 v-else class="text-2xl font-semibold">{{ task.doc.title }}</h1>
        <div class="ml-2 flex shrink-0 space-x-1">
          <template v-if="!editTaskTitle">
            <div
              v-if="task.doc.is_completed"
              class="flex shrink-0 items-center rounded-md bg-green-100 px-2 py-1 text-base text-green-800"
              :title="
                [
                  `Completed on: ${$dayjs(task.doc.completed_at).format(
                    'D MMM YYYY, HH:mm A'
                  )}`,
                  `Completed by: ${$user(task.doc.completed_by).full_name}`,
                ].join('\n')
              "
            >
              <FeatherIcon
                name="check"
                class="mr-1 w-4 text-green-800/70"
                :strokeWidth="3"
              />
              <span> Completed </span>
            </div>
            <Dropdown
              :button="{ icon: 'more-horizontal' }"
              :options="[
                {
                  label: 'Edit title',
                  icon: 'edit',
                  handler: () => {
                    editTaskTitle = true
                    // $nextTick(() => $refs.taskTitle.focus())
                  },
                },
                {
                  label: 'Mark as complete',
                  icon: 'check',
                  handler: () => {
                    task.setValue.submit({
                      is_completed: true,
                      completed_by: $user().name,
                      completed_at: $dayjs().format('YYYY-MM-DD HH:mm:ss'),
                    })
                  },
                  condition: () => !task.doc.is_completed,
                },
                {
                  label: 'Mark as incomplete',
                  icon: 'rotate-ccw',
                  handler: () => {
                    task.setValue.submit({
                      is_completed: false,
                      completed_by: '',
                      completed_at: '',
                    })
                  },
                  condition: () => task.doc.is_completed,
                },
                {
                  label: 'Delete this task',
                  icon: 'trash',
                  appearance: 'danger',
                  handler: deleteTask,
                },
              ]"
              placement="right"
            />
          </template>
          <template v-if="editTaskTitle">
            <Button appearance="primary" @click="updateTaskTitle()">
              Save
            </Button>
            <Button
              @click="
                () => {
                  editTaskTitle = false
                  task.reload()
                }
              "
            >
              Discard
            </Button>
          </template>
        </div>
      </div>
      <div class="mt-1 flex items-center text-sm text-gray-600">
        <span>
          Created on {{ $dayjs(task.doc.creation).format('D MMM, YYYY') }} by
        </span>
        <span class="ml-1">
          <UserInfo :email="task.doc.owner" v-slot="{ user }">
            {{ user.full_name }}
          </UserInfo>
        </span>
        <template v-if="task.doc.is_completed">
          <span>&nbsp;&middot;&nbsp;</span>
          Completed on
          {{ $dayjs(task.doc.completed_at).format('D MMM, YYYY') }} by
          {{ $user(task.doc.completed_by).full_name }}
        </template>
      </div>
    </div>
    <div class="grid grid-cols-8 gap-4 border-b pb-5">
      <div class="col-span-8 sm:col-span-6">
        <ReadmeEditor
          class="min-h-full"
          :resource="task"
          fieldname="description"
          placeholder="Write a description..."
        />
      </div>
      <div class="col-span-8 space-y-4 sm:col-span-2">
        <div class="w-full">
          <label class="text-sm text-gray-600">Assignee</label>
          <Autocomplete
            class="mt-2"
            placeholder="Assign a user"
            :options="assignableUsers"
            :value="task.doc.assigned_to"
            @change="
              (option) => {
                task.setValue.submit({ assigned_to: option?.value || '' })
              }
            "
          />
        </div>
        <div class="w-full">
          <label class="text-sm text-gray-600">Due Date</label>
          <input
            type="date"
            class="form-input mt-2 w-full"
            :class="task.doc.due_date ? 'text-gray-700' : 'text-gray-500'"
            :value="task.doc.due_date"
            @change="
              (e) => {
                task.setValue.submit({
                  due_date: e.target.value,
                })
              }
            "
          />
        </div>
      </div>
    </div>
    <CommentsArea class="flex-1" doctype="Team Task" :name="task.doc.name" />
  </div>
</template>
<script>
import { Avatar, TextEditor, Autocomplete, Dropdown } from 'frappe-ui'
import CommentsArea from './CommentsArea.vue'
import ReadmeEditor from '@/components/ReadmeEditor.vue'
import { focus } from '@/directives'

export default {
  name: 'ProjectTaskDetail',
  props: ['project', 'taskId'],
  directives: {
    focus,
  },
  components: {
    TextEditor,
    Avatar,
    CommentsArea,
    Autocomplete,
    ReadmeEditor,
    Dropdown,
  },
  data() {
    return {
      editTaskTitle: false,
    }
  },
  resources: {
    task() {
      return {
        type: 'document',
        doctype: 'Team Task',
        name: this.taskId,
        setValue: {
          onError(e) {
            let message = e.messages ? e.messages.join('\n') : e.message
            this.$toast({
              title: 'Task Update Error',
              text: message,
              icon: 'alert-circle',
              iconClasses: 'text-red-600',
            })
          },
        },
      }
    },
  },
  methods: {
    deleteTask() {
      this.$dialog({
        title: 'Delete Task',
        message: 'Are you sure you want to delete this task?',
        actions: [
          {
            label: 'Delete',
            appearance: 'danger',
            handler: ({ close }) => {
              return this.task.delete.submit(null, {
                onSuccess: () => {
                  this.$router.back()
                  close()
                },
              })
            },
          },
          {
            label: 'Cancel',
          },
        ],
      })
    },
    updateTaskTitle() {
      if (this.task.doc.title) {
        this.task.setValue.submit({ title: this.task.doc.title })
      } else {
        this.task.reload()
      }
      this.editTaskTitle = false
    },
    $tasks() {
      return this.$getListResource(['Project Tasks', this.task.doc.project])
    },
  },
  computed: {
    task() {
      return this.$resources.task
    },
    assignableUsers() {
      return this.$users.data
        .filter((user) => user.name != this.task.doc.assigned_to)
        .map((user) => ({
          label: user.full_name,
          value: user.name,
        }))
    },
  },
}
</script>
