<template>
  <div
    class="container py-8 mx-auto"
    style="height: calc(100vh - 5.25rem)"
    v-if="$resources.document.data"
  >
    <div class="max-w-2xl mx-auto">
      <input
        type="text"
        v-model="title"
        class="bg-transparent border-none rounded-lg focus:ring-0 focus:bg-gray-200"
        @change="onUpdate()"
      />
    </div>
    <div
      class="relative max-w-2xl min-h-full p-6 mx-auto mt-2 bg-white shadow rounded-xl"
    >
      <LoadingIndicator
        v-if="$resources.updateDocument.loading"
        class="absolute top-0 right-0 mt-4 mr-4 text-gray-600"
      />
      <TextEditor
        :content="content"
        @change="
          (updatedContent) => {
            content = updatedContent
            onUpdate()
          }
        "
      />
    </div>
  </div>
</template>
<script>
import { LoadingIndicator, TextEditor, debounce } from 'frappe-ui'

export default {
  name: 'EditDocument',
  props: ['documentId'],
  components: {
    LoadingIndicator,
    TextEditor,
  },
  data() {
    return {
      title: '',
      content: '',
    }
  },
  resources: {
    document() {
      return {
        method: 'teams.api.get_document',
        params: {
          name: this.documentId,
        },
        onSuccess(document) {
          this.title = document.title
          this.content = document.content
        },
        auto: true,
      }
    },
    updateDocument: {
      method: 'teams.api.update_document',
    },
  },
  methods: {
    onUpdate: debounce(function () {
      if (!this.content) return
      this.$resources.updateDocument.submit({
        name: this.documentId,
        title: this.title,
        content: this.content,
      })
    }, 500),
  },
}
</script>
