<template>
  <PageEditor :pageId="pageId" />
</template>
<script>
import PageEditor from './PageEditor.vue'

export default {
  name: 'ProjectPage',
  props: ['project', 'pageId'],
  components: { PageEditor },
}
</script>
