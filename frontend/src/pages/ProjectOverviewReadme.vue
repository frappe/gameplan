<template>
  <ReadmeEditor :resource="project" fieldname="readme" :border="false" />
</template>
<script>
import ReadmeEditor from '@/components/ReadmeEditor.vue'
export default {
  name: 'ProjectOverviewReadme',
  props: ['project'],
  components: { ReadmeEditor },
}
</script>
