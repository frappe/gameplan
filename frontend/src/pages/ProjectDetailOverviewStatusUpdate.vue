<template>
  <div>
    <h2 class="text-lg font-bold">Activity</h2>
    <div class="mt-6 mb-8">
      <Button
        icon-left="edit-3"
        @click="writingStatusUpdate = true"
        v-if="!writingStatusUpdate"
      >
        Write a status update
      </Button>
      <div v-if="writingStatusUpdate">
        <Input
          label="Project Status"
          type="select"
          :options="['', 'On Track', 'Off Track', 'Completed']"
          v-model="statusUpdate.status"
        />
        <div class="mt-4">
          <label for="#status-update" class="mb-2 text-sm text-gray-700">
            Summary
          </label>
          <TextEditor
            id="status-update"
            class="w-full px-3 py-2 prose-sm prose max-w-[unset] rounded-lg bg-gray-50"
            editor-class="min-h-[6rem]"
            placeholder="Project updates..."
            :showMenu="true"
            :content="statusUpdate.content"
            @change="(val) => (statusUpdate.content = val)"
          />
        </div>
        <div class="mt-4 space-x-2">
          <Button
            appearance="primary"
            @click="$resources.statusUpdate.submit()"
            :loading="$resources.statusUpdate.loading"
          >
            Submit
          </Button>
          <Button
            @click="
              () => {
                writingStatusUpdate = false
                statusUpdate = { content: '', status: '' }
              }
            "
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>

    <div v-for="activity in $resources.activities.data" :key="activity.date">
      <div class="my-6">
        <template v-if="activity.type === 'info'">
          <div class="flex space-x-2">
            <div class="flex justify-center w-8">
              <FeatherIcon name="circle" class="w-4 text-gray-500" />
            </div>
            <div class="text-base text-gray-700">
              {{ activity.title }} by {{ activity.user }}
            </div>
          </div>
        </template>
        <template v-else-if="activity.type === 'content'">
          <div class="flex space-x-2">
            <Avatar :label="activity.user" />
            <div>
              <div class="py-1 text-lg font-semibold">
                {{ activity.status }}
              </div>
              <div v-html="activity.content" class="prose-sm prose"></div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
export default {
  name: 'ProjectDetailOverviewStatusUpdate',
  props: ['project'],
  components: { Avatar, TextEditor },
  data() {
    return {
      writingStatusUpdate: false,
      statusUpdate: {
        content: '',
        status: '',
      },
    }
  },
  resources: {
    activities() {
      return {
        method: 'teams.api.project_activities',
        params: {
          project: this.project.name,
        },
        auto: true,
      }
    },
    statusUpdate() {
      return {
        method: 'frappe.client.insert',
        params: {
          doc: {
            doctype: 'Team Project Status Update',
            project: this.project.name,
            status: this.statusUpdate.status,
            content: this.statusUpdate.content,
          },
        },
        onSuccess() {
          this.resetStatusUpdate()
          this.$resources.activities.reload()
        },
      }
    },
  },
  methods: {
    resetStatusUpdate() {
      this.writingStatusUpdate = false
      this.statusUpdate = { content: '', status: '' }
    },
  },
}
</script>
