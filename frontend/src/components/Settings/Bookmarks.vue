<template>
  <div class="flex min-h-0 flex-col">
    <h2 class="text-xl font-semibold">Bookmarked Discussions</h2>
    <div class="mt-6 divide-y overflow-y-auto pb-16">
      <DiscussionList
        v-if="bookmarks.length"
        ref="discussionList"
        routeName="ProjectDiscussion"
        :listOptions="{ filters }"
        :key="JSON.stringify(filters)"
        @click="handleDiscussionClick"
      />
      <p v-else class="text-base text-gray-900">No bookmarks</p>
    </div>
  </div>
</template>
<script>
import DiscussionList from '../DiscussionList.vue'

export default {
  name: 'BookmarksTabDialog',
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
      return this.bookmarks && this.bookmarks.length
        ? { name: this.bookmarks }
        : {}
    },
  },
  methods: {
    handleDiscussionClick() {
      this.$emit('close-dialog')
    },
  },
}
</script>
