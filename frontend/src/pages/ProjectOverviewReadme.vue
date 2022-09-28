<template>
  <ReadmeEditor
    :resource="project"
    fieldname="readme"
    :border="false"
    :editable="!project.doc.archived_at"
  />
</template>
<script>
import ReadmeEditor from '@/components/ReadmeEditor.vue'
export default {
  name: 'ProjectOverviewReadme',
  props: ['project'],
  components: { ReadmeEditor },
}
</script>
