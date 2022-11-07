<template>
  <ReadmeEditor
    class="my-6"
    :resource="profile"
    :editable="$isSessionUser(profile.doc.user)"
    fieldname="readme"
    :placeholder="
      $isSessionUser(profile.doc.user)
        ? 'Write a brief introduction of yourself...'
        : 'No introduction'
    "
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
