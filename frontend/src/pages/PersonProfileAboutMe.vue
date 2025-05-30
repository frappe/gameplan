<template>
  <div class="mt-7 pb-16">
    <h2 class="mb-3 text-lg font-semibold text-ink-gray-8">About</h2>
    <ReadmeEditor
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
  </div>
</template>
<script>
import ReadmeEditor from '@/components/ReadmeEditor.vue'
export default {
  name: 'PersonProfileAboutMe',
  props: ['profile'],
  components: { ReadmeEditor },
}
</script>
