<template>
  <div class="p-6">
    <div class="flex items-start justify-between">
      <div class="w-full">
        <div>
          <label class="text-base text-gray-700">Title</label>
        </div>
        <input
          type="text"
          class="w-4/5 px-2 py-1 mt-1 text-xl font-semibold bg-gray-100 border-0 rounded-lg focus:ring-0"
          ref="title"
          v-model="title"
        />
      </div>
      <div class="space-x-2 shrink-0">
        <Button
          appearance="primary"
          :loading="$resources.newUpdate.loading"
          @click="$resources.newUpdate.submit({ title, status, content })"
        >
          Publish
        </Button>
        <Button :route="{ name: 'ProjectDetailDiscussions' }">Discard</Button>
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
      content: '',
    }
  },
  mounted() {
    this.$refs.title.focus()
  },
  resources: {
    newUpdate() {
      return {
        method: 'frappe.client.insert',
        makeParams({ title, content }) {
          return {
            doc: {
              doctype: 'Team Project Discussion',
              project: this.project.doc.name,
              title,
              content,
            },
          }
        },
        validate(params) {
          if (!params.doc.title) {
            return `Please enter title before publishing.`
          }
        },
        onSuccess(doc) {
          this.$router.replace({
            name: 'ProjectDetailUpdate',
            params: { updateId: doc.name },
          })
          this.$getListResource([
            'Project Updates',
            { project: this.project.doc.name },
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
