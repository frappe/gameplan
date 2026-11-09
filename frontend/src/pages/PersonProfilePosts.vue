<template>
  <div class="pb-16 -mx-3">
    <DiscussionList :filters="{ owner: profile.doc.user }" :showPinned="false" showCommunity />
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
