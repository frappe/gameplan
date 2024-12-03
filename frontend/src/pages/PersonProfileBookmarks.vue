<template>
  <div class="pb-16">
    <DiscussionList
      ref="discussionList"
      routeName="ProjectDiscussion"
      :listOptions="{ filters: { user_bookmarks: true } }"
    />
  </div>
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'

export default {
  name: 'PersonProfileBookmarks',
  methods: {
    handleDiscussionClick() {
      this.$emit('close-dialog')
    },
    components: { DiscussionList },
  },
}
</script>
