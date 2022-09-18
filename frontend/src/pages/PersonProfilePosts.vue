<template>
  <div class="mt-6">
    <DiscussionList
      :filters="{ owner: profile.doc.user }"
      routeName="ProjectDiscussion"
    />
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
