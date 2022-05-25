<template>
  <div class="flex flex-col" v-if="task && task.doc">
    <div class="flex-shrink-0">
      <div class="flex items-center h-10 px-5 text-sm border-b">
        <span class="text-gray-600">
          Created on {{ $dayjs(task.doc.creation).format('d MMM, YYYY') }} by
        </span>
        <span class="ml-1 text-gray-900">
          <UserInfo :email="task.doc.owner" v-slot="{ user }">
            {{ user.full_name }}
          </UserInfo>
        </span>
      </div>
      <div class="flex items-center justify-between px-5 pt-5">
        <input
          type="text"
          class="w-1/2 p-1 -mx-1 text-2xl font-semibold border-none rounded-md focus:outline-none focus:bg-gray-100 focus:ring-0"
          v-model="task.doc.title"
          @input="
            () => {
              if (task.doc.title) {
                task.setValueDebounced.submit(
                  { title: task.doc.title },
                  {
                    onSuccess() {
                      $tasks().setData((data) => {
                        data[task.doc.project_section].find(
                          (t) => t.name === task.doc.name
                        ).title = task.doc.title
                        return data
                      })
                      $emit('task-update')
                    },
                  }
                )
              }
            }
          "
        />
        <div class="flex space-x-1">
          <Button icon="trash-2" @click="deleteTask"></Button>
          <Button
            icon="chevrons-right"
            :route="{ name: 'ProjectDetailTasks' }"
          />
        </div>
      </div>
      <div class="mt-6 space-y-5 border-b">
        <div class="grid grid-cols-4 px-5 text-base">
          <div class="flex items-center text-gray-600">
            <FeatherIcon class="w-4 h-4" name="user" />
            <span class="ml-4">Assignee</span>
          </div>
          <span class="text-gray-900">
            WIP
            <!-- <AssignUser
              class="w-full h-full text-sm text-gray-700"
              :class="
                task.assignedUser || task.isActive
                  ? ''
                  : 'opacity-0 group-hover:opacity-100'
              "
              :users="users"
              :assignedUser="task.assignedUser"
              @update:assigned-user="updateAssignedUser(task, $event)"
            /> -->
          </span>
        </div>
        <div class="grid grid-cols-4 px-5 text-base">
          <div class="flex items-center text-gray-600">
            <FeatherIcon class="w-4 h-4" name="calendar" />
            <span class="ml-4">Due Date</span>
          </div>
          <span class="text-gray-900">
            <!-- {{ $dayjs(task.doc.due_date).format('d MMM, YYYY') }} -->
            <input
              type="date"
              class="w-full h-full p-0 text-sm bg-transparent border-none focus:outline-none"
              :class="task.doc.due_date ? 'text-gray-700' : 'text-gray-500'"
              :value="task.doc.due_date"
              @change="
                (e) => {
                  task.doc.due_date = e.target.value
                  task.setValue.submit({
                    due_date: task.doc.due_date,
                  })
                }
              "
            />
          </span>
        </div>
        <div class="flex items-start px-5 text-base">
          <FeatherIcon class="w-4 h-4 text-gray-600" name="align-left" />
          <TextEditor
            class="ml-4 -mt-2"
            editor-class="min-h-[4rem]"
            :content="task.doc.description"
            placeholder="Add task description"
            @change="
              (val) => task.setValueDebounced.submit({ description: val })
            "
            :bubbleMenu="true"
          />
        </div>
      </div>
    </div>
    <CommentsArea
      class="flex-1 min-h-0 overflow-auto bg-gray-50"
      :task="$resources.task"
    />
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import CommentsArea from './CommentsArea.vue'
import AssignUser from '@/components/AssignUser.vue'

export default {
  name: 'ProjectTaskDetail',
  props: ['project', 'taskId'],
  components: {
    TextEditor,
    Avatar,
    CommentsArea,
    AssignUser,
  },
  resources: {
    task() {
      return {
        type: 'document',
        doctype: 'Team Task',
        name: this.taskId,
        setValue: {
          onSuccess(task) {
            this.$tasks().setData((bySection) => {
              for (let t of bySection[task.project_section]) {
                if (t.name === task.name) {
                  Object.assign(t, task)
                }
              }
              return bySection
            })
          },
        },
      }
    },
  },
  methods: {
    deleteTask() {
      this.task.delete.submit()
      this.$router.back()
      this.$tasks().setData((bySection) => {
        bySection[this.task.project_section] = bySection[
          this.task.project_section
        ].filter((task) => task.name !== this.task.name)
        return bySection
      })
    },
    $tasks() {
      return this.$getListResource(['Project Tasks', this.task.doc.project])
    },
  },
  computed: {
    task() {
      return this.$resources.task
    },
  },
}
</script>
