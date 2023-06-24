<template>
  <div class="pb-16">
    <DiscussionList
      :listOptions="{ filters: { participator: profile.doc.user } }"
      routeName="ProjectDiscussion"
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
