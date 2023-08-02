<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
  >
    <PageBreadcrumbs
      class="h-7"
      :items="[
        { label: 'My Pages', route: { name: 'MyPages' } },
        { label: title, route: { name: 'Page', params: { slug: slug } } },
      ]"
    />
  </header>
  <div class="mx-auto w-full max-w-4xl px-5">
    <PageEditor :pageId="pageId" />
  </div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui'
import PageEditor from './PageEditor.vue'

export default {
  name: 'Page',
  props: ['pageId', 'slug'],
  components: { PageEditor },
  computed: {
    title() {
      let page = getCachedDocumentResource('GP Page', this.pageId)
      return page?.doc?.title || this.pageId
    },
  },
}
</script>
