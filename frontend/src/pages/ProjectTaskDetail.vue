<template>
  <div class="flex h-full flex-1" v-if="$resources.task.doc">
    <div class="flex-1">
      <div class="relative p-6">
        <div
          class="absolute right-0 top-0 p-6"
          v-show="$resources.task.setValueDebounced.loading"
        >
          <LoadingText
            v-if="!$resources.task.setValueDebounced.error"
            text="Saving..."
          />
          <ErrorMessage :message="$resources.task.setValueDebounced.error" />
        </div>
        <input
          type="text"
          placeholder="Title"
          class="w-full rounded-md border-none p-0 text-2xl font-semibold text-gray-900 focus:outline-none focus:ring-0"
          @input="
            $resources.task.setValueDebounced.submit({
              title: $event.target.value,
            })
          "
          v-model="$resources.task.doc.title"
          v-focus
        />
        <TextEditor
          ref="readme"
          editor-class="prose-sm max-w-none"
          placeholder="Description"
          :content="$resources.task.doc.description"
          @change="(val) => ($resources.task.doc.description = val)"
          :bubbleMenu="true"
          :floating-menu="true"
        />
        <CommentsList class="mt-8" doctype="GP Task" :name="taskId" />
      </div>
    </div>
    <div class="w-[20rem] shrink-0 border-l">
      <div
        class="grid grid-cols-2 items-center gap-y-6 p-6 text-base text-gray-700"
      >
        <div>Assignee</div>
        <div>
          <Autocomplete
            placeholder="Assign a user"
            :options="assignableUsers"
            :value="$resources.task.doc.assigned_to"
            @change="
              (option) => {
                $resources.task.setValue.submit({
                  assigned_to: option?.value || '',
                })
              }
            "
          />
        </div>
        <div>Due Date</div>
        <div>
          <TextInput
            type="date"
            placeholder="Due date"
            v-model="$resources.task.doc.due_date"
            @change="
              $resources.task.setValue.submit({
                due_date: $event.target.value,
              })
            "
          />
        </div>
        <div>Status</div>
        <div>
          <Dropdown :options="statusOptions">
            <Button>
              <template #prefix>
                <TaskStatusIcon :status="$resources.task.doc.status" />
              </template>
              {{ $resources.task.doc.status || 'Set status' }}
            </Button>
          </Dropdown>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { h } from 'vue'
import TextEditor from '@/components/TextEditor.vue'
import ReadmeEditor from '@/components/ReadmeEditor.vue'
import CommentsArea from '@/components/CommentsArea.vue'
import { focus } from '@/directives'
import { Autocomplete, Dropdown, LoadingText, TextInput } from 'frappe-ui'
import CommentsList from '@/components/CommentsList.vue'
import TaskStatusIcon from '@/components/icons/TaskStatusIcon.vue'

export default {
  name: 'TaskDetail',
  props: ['project', 'taskId'],
  directives: { focus },
  resources: {
    task() {
      return {
        type: 'document',
        doctype: 'GP Task',
        name: this.taskId,
        whitelistedMethods: {
          trackVisit: 'track_visit',
        },
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
        onSuccess(doc) {
          if (
            this.$route.name === 'ProjectTaskDetail' &&
            Number(this.$route.params.taskId) === doc.name
          ) {
            this.$resources.task.trackVisit.submit()
          }
        },
      }
    },
  },
  computed: {
    assignableUsers() {
      return this.$users.data
        .filter((user) => user.name != this.$resources.task.doc.assigned_to)
        .map((user) => ({
          label: user.full_name,
          value: user.name,
        }))
    },
    statusOptions() {
      return ['Backlog', 'Todo', 'In Progress', 'Done', 'Canceled'].map(
        (status) => {
          return {
            icon: () => h(TaskStatusIcon, { status }),
            label: status,
            onClick: () => this.$resources.task.setValue.submit({ status }),
          }
        }
      )
    },
  },
  components: {
    ReadmeEditor,
    TextEditor,
    CommentsArea,
    Autocomplete,
    TextInput,
    Dropdown,
    CommentsList,
    TaskStatusIcon,
    LoadingText,
  },
}
</script>
