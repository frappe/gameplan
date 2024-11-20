<template>
  <div>
    <DiscussionListByData :discussions="$resources.discussions?.data" />
  </div>
</template>

<script>
import DiscussionListByData from '@/components/DiscussionListByData.vue'

export default {
  name: 'PersonProfileBookmarks',
  components: {
    DiscussionListByData,
  },
  data() {
    return {
      discussionFilters: [],
    }
  },
  resources: {
    bookmarks() {
      return {
        type: 'list',
        doctype: 'GP Bookmark',
        fields: ['discussion'],
        filters: {
          user: this.$user().name,
        },
        auto: true,
        onSuccess(data) {
          this.discussionFilters = data.map((record) =>
            Number(record.discussion),
          )
        },
      }
    },
    discussions() {
      return {
        type: 'list',
        doctype: 'GP Discussion',
        fields: [
          'name',
          'title',
          'project',
          'team',
          'creation',
          'owner',
          'last_post_by',
          'last_post_at',
          'slug',
          'comments_count',
        ],
        auto: true,
        filters: {
          name: ['in', this.discussionFilters],
        },
      }
    },
  },
}
</script>
