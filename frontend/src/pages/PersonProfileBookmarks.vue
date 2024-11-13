<template>
  <div class="pb-16">
    <DiscussionList
      v-if="bookmarks.length"
      ref="discussionList"
      routeName="ProjectDiscussion"
      :listOptions="{ filters }"
      :key="JSON.stringify(filters)"
      @click="handleDiscussionClick"
    />
  </div>
</template>
<script>
import DiscussionList from '@/components/DiscussionList.vue'

export default {
  name: 'PersonProfileBookmarks',
  data() {
    return {
      bookmarks: [],
    }
  },
  resources: {
    bookmark() {
      return {
        type: 'resource',
        url: 'gameplan.api.get_bookmarks',
        auto: true,
        onSuccess(data) {
          if (data) {
            this.bookmarks = data.map((record) => Number(record.discussion))
          }
        },
      }
    },
  },
  computed: {
    filters() {
      return this.bookmarks && this.bookmarks.length ? { name: this.bookmarks } : {}
    },
  },
  methods: {
    handleDiscussionClick() {
      this.$emit('close-dialog')
    },
    components: { DiscussionList },
  },
}
</script>
