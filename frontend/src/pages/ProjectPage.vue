<template>
  <div class="py-6" v-if="page.doc">
    <div class="px-[70px]">
      <input
        class="w-full border-0 p-0 pt-4 text-5xl font-semibold focus:outline-none focus:ring-0"
        type="text"
        :value="page.doc.title"
        @input="page.setValueDebounced.submit({ title: $event.target.value })"
        ref="titleInput"
      />
      <hr class="my-4" />
    </div>
    <TextEditor
      editor-class="rounded-b-lg max-w-[unset] prose-sm pb-[50vh] px-[70px]"
      :content="page.doc.content"
      @change="page.setValueDebounced.submit({ content: $event })"
      placeholder="Start writing here..."
    />
  </div>
</template>
<script>
import { TextEditor } from 'frappe-ui'

export default {
  name: 'ProjectPage',
  props: ['project', 'pageId'],
  resources: {
    page() {
      return {
        type: 'document',
        doctype: 'GP Page',
        name: this.pageId,
        realtime: true,
      }
    },
  },
  mounted() {
    setTimeout(() => {
      this.$refs.titleInput.focus()
    }, 100)
  },
  computed: {
    page() {
      return this.$resources.page
    },
  },
  components: { TextEditor },
}
</script>
