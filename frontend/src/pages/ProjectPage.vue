<template>
  <div class="py-6" v-if="page.doc">
    <div class="md:px-[70px]">
      <input
        class="w-full border-0 p-0 pt-4 text-5xl font-semibold focus:outline-none focus:ring-0"
        type="text"
        :value="page.doc.title"
        @input="
          page.setValueDebounced.submit(
            { title: $event.target.value },
            { onSuccess: updateUrlSlug }
          )
        "
        ref="titleInput"
      />
      <hr class="my-4" />
    </div>
    <TextEditor
      editor-class="rounded-b-lg max-w-[unset] prose-sm pb-[50vh] md:px-[70px]"
      :content="page.doc.content"
      @change="page.setValueDebounced.submit({ content: $event })"
      placeholder="Start writing here..."
      :bubbleMenu="true"
    />
  </div>
</template>
<script>
import { TextEditor } from 'frappe-ui'

export default {
  name: 'ProjectPage',
  props: ['project', 'pageId'],
  components: { TextEditor },
  resources: {
    page() {
      return {
        type: 'document',
        doctype: 'GP Page',
        name: this.pageId,
        realtime: true,
        onSuccess() {
          this.updateUrlSlug()
        },
      }
    },
  },
  mounted() {
    setTimeout(() => {
      this.$refs.titleInput.focus()
    }, 100)
  },
  methods: {
    updateUrlSlug() {
      if (
        !this.$route.params.slug ||
        this.$route.params.slug !== this.page.doc.slug
      ) {
        this.$router.replace({
          name: 'ProjectPage',
          params: {
            ...this.$route.params,
            slug: this.page.doc.slug,
          },
          query: this.$route.query,
        })
      }
    },
  },
  computed: {
    page() {
      return this.$resources.page
    },
  },
}
</script>
