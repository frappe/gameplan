<template>
  <div class="pb-16">
    <DiscussionList :filters="{ owner: profile.doc.user }" :showPinned="false" />
  </div>
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'
export default {
  name: 'PersonProfilePosts',
  props: ['profile'],
  components: { DiscussionList },
}
</script>
