<template>
  <div v-if="task && task.doc">
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
        <Button icon="chevrons-right" :route="{ name: 'ProjectDetailTasks' }" />
      </div>
    </div>
    <div class="px-5 pt-5 pb-5 border-b">
      <label class="text-sm text-gray-600">Description</label>
      <TextEditor
        editor-class=" min-h-[4rem]"
        :content="task.doc.description"
        placeholder="Add task description"
        @change="(val) => task.setValueDebounced.submit({ description: val })"
        :bubbleMenu="true"
      />
    </div>
  </div>
</template>
<script>
import { TextEditor } from 'frappe-ui'
export default {
  name: 'ProjectTaskDetail',
  props: ['project', 'taskId'],
  components: {
    TextEditor,
  },
  resources: {
    task() {
      return {
        type: 'document',
        doctype: 'Team Task',
        name: this.taskId,
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
