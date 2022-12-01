<template>
  <div class="flex flex-col">
    <div class="py-5">
      <h1 class="mb-4 text-2xl font-semibold">New Task</h1>
      <Input type="text" placeholder="Title" v-model="title" />
      <div class="mt-4">
        <div class="relative mt-2 rounded-md border px-3 py-2">
          <TextEditor
            editor-class="min-h-[4rem] prose-sm"
            :content="description"
            placeholder="Description"
            @change="(val) => (description = val)"
            :bubbleMenu="true"
          />
        </div>
      </div>
      <div class="mt-4 space-x-2">
        <Button
          appearance="primary"
          @click="$resources.createTask.submit()"
          :loading="$resources.createTask.loading"
        >
          Create new task
        </Button>
        <Button :route="{ name: 'ProjectTasks' }">Cancel</Button>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Autocomplete, Input } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'

export default {
  name: 'ProjectTaskNew',
  props: ['project'],
  components: {
    Input,
    TextEditor,
    Avatar,
    Autocomplete,
  },
  data() {
    return {
      title: '',
      description: '',
    }
  },
  resources: {
    createTask: {
      url: 'frappe.client.insert',
      makeParams() {
        return {
          doc: {
            doctype: 'Team Task',
            project: this.project.doc.name,
            title: this.title,
            description: this.description,
          },
        }
      },
      onSuccess(task) {
        this.$router.replace({
          name: 'ProjectTaskDetail',
          params: {
            teamId: this.project.doc.team,
            projectId: this.project.doc.name,
            taskId: task.name,
          },
        })
      },
    },
  },
}
</script>
