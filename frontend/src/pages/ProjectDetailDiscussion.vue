<template>
  <div class="flex">
    <DiscussionView class="w-full" :postId="postId" />
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionView from '@/components/DiscussionView.vue'

export default {
  name: 'ProjectDetailUpdate',
  props: ['project', 'postId'],
  components: {
    TextEditor,
    Avatar,
    Link,
    Reactions,
    DiscussionList,
    DiscussionView,
  },
  methods: {
    isActive(update) {
      return Number(this.$route.params.postId) === update.name
    },
  },
}
</script>
