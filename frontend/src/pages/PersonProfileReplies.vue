<template>
  <div class="pb-16 -mx-3">
    <DiscussionList
      :filters="{ participator: profile.doc.user }"
      :show-pinned="false"
      show-community
    />
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
