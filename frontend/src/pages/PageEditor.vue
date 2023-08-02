<template>
  <div class="py-6" v-if="page.doc">
    <div class="md:px-[70px]">
      <input
        class="text-5xl w-full border-0 p-0 pt-4 font-semibold focus:outline-none focus:ring-0"
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
      <div class="mt-2 text-sm text-gray-600">
        Updated by {{ $user(page.doc.modified_by).full_name }} on
        {{ $dayjs(page.doc.modified).format('LLL') }}
      </div>
      <hr class="mb-4 mt-2" />
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
  name: 'PageEditor',
  props: ['pageId'],
  components: { TextEditor },
  resources: {
    page() {
      return {
        type: 'document',
        doctype: 'GP Page',
        name: this.pageId,
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
    this.setupRealtime()
  },
  beforeUnmount() {
    this.removeRealtime()
  },
  methods: {
    updateUrlSlug() {
      if (
        !this.$route.params.slug ||
        this.$route.params.slug !== this.page.doc.slug
      ) {
        this.$router.replace({
          name: this.page.doc.project ? 'ProjectPage' : 'Page',
          params: {
            ...this.$route.params,
            slug: this.page.doc.slug,
          },
          query: this.$route.query,
        })
      }
    },
    onRealtime({ doctype, name, user }) {
      if (
        doctype === 'GP Page' &&
        name == this.pageId &&
        user != this.$user().name
      ) {
        this.$resources.page.reload()
      }
    },
    setupRealtime() {
      this.$socket.emit('doctype_subscribe', 'GP Page')
      this.$socket.on('list_update', this.onRealtime)
    },
    removeRealtime() {
      this.$socket.emit('doctype_unsubscribe', 'GP Page')
      this.$socket.off('list_update', this.onRealtime)
    },
  },
  computed: {
    page() {
      return this.$resources.page
    },
  },
}
</script>
