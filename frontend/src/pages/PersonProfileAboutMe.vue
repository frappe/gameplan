<template>
  <ReadmeEditor
    class="mt-6"
    :resource="profile"
    :editable="$isSessionUser(profile.doc.user)"
    fieldname="readme"
    placeholder="Write a brief introduction of yourself..."
    :border="false"
  />
</template>
<script>
import ReadmeEditor from '@/components/ReadmeEditor.vue'
export default {
  name: 'PersonProfileAboutMe',
  props: ['profile'],
  components: { ReadmeEditor },
}
</script>
