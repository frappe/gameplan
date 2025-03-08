<template>
  <div class="pb-16">
    <DiscussionList :filters="{ participator: profile.doc.user }" :show-pinned="false" />
  </div>
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'
export default {
  name: 'PersonProfileReplies',
  props: ['profile'],
  components: { DiscussionList },
}
</script>
