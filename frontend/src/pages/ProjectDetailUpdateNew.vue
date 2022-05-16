<template>
  <div class="p-6">
    <div class="flex items-start justify-between">
      <div>
        <div>
          <label class="text-base text-gray-700">Title</label>
        </div>
        <input
          type="text"
          class="px-2 py-1 mt-1 text-xl font-semibold bg-gray-100 border-0 rounded-lg focus:ring-0"
          placeholder="Project is on track..."
          ref="title"
          v-model="title"
        />
      </div>
      <div class="space-x-2">
        <Button
          appearance="primary"
          :loading="$resources.newUpdate.loading"
          @click="$resources.newUpdate.submit({ title, status, content })"
        >
          Publish
        </Button>
        <Button :route="{ name: 'ProjectDetailUpdate' }">Discard</Button>
      </div>
    </div>

    <div class="mt-3">
      <div>
        <label class="text-base text-gray-700">Status</label>
      </div>
      <div class="mt-1 space-x-2">
        <Button
          :appearance="d.name === status ? d.appearance : 'secondary'"
          v-for="d in statuses"
          :key="d.name"
          @click="status = d.name"
        >
          <span :class="d.name !== status ? d.textColor : null">
            {{ d.name }}
          </span>
        </Button>
      </div>
    </div>
    <div class="mt-3">
      <label class="text-base text-gray-700">Summary</label>
    </div>
    <TextEditor
      class="mt-1"
      editor-class="px-3 py-2 border rounded-b-lg max-w-[unset] min-h-[20rem]"
      :content="content"
      @change="(val) => (content = val)"
      :bubbleMenu="true"
      :fixedMenu="true"
    />
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'

export default {
  name: 'ProjectDetailUpdateNew',
  props: ['project'],
  components: { TextEditor, Avatar },
  data() {
    return {
      title: '',
      status: '',
      content: `
        <h3>What we've accomplished</h3>
        <p></p>
        <h3>What's blocked</h3>
        <p></p>
        <h3>Next Steps</h3>
        <p></p>
      `,
    }
  },
  mounted() {
    this.$refs.title.focus()
  },
  resources: {
    newUpdate() {
      return {
        method: 'frappe.client.insert',
        makeParams({ title, status, content }) {
          return {
            doc: {
              doctype: 'Team Project Status Update',
              project: this.project.doc.name,
              title,
              status,
              content,
            },
          }
        },
        validate(params) {
          if (!params.doc.title) {
            return `Please enter title before publishing.`
          }
          if (!params.doc.status) {
            return `Please select project status before publishing.`
          }
        },
        onSuccess() {
          this.$router.replace({ name: 'ProjectDetailUpdate' })
          this.$getListResource([
            'Project Updates',
            this.project.doc.name,
          ]).reload()
          this.title = ''
          this.status = null
          this.content = ''
        },
        onError(e) {
          let message = e.messages ? e.messages.join('\n') : e.message
          this.$toast({
            title: 'Project Update Error',
            text: message,
            icon: 'alert-circle',
            iconClasses: 'text-red-600',
          })
        },
      }
    },
  },
  computed: {
    statuses() {
      return [
        {
          name: 'On Track',
          textColor: 'text-green-600',
          appearance: 'success',
        },
        {
          name: 'At Risk',
          textColor: 'text-yellow-600',
          appearance: 'warning',
        },
        { name: 'Off Track', textColor: 'text-red-600', appearance: 'danger' },
      ]
    },
  },
}
</script>
