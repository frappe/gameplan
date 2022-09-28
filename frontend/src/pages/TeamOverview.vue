<template>
  <div class="pt-6">
    <ReadmeEditor
      :resource="team"
      fieldname="readme"
      :border="false"
      :editable="!team.doc.archived_at"
    />
  </div>
</template>
<script>
import ReadmeEditor from '@/components/ReadmeEditor.vue'
export default {
  name: 'TeamOverview',
  props: ['team'],
  components: { ReadmeEditor },
}
</script>
