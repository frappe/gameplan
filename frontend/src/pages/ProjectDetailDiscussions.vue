<template>
  <div class="flex">
    <div class="w-full h-full py-6">
      <div class="flex items-center justify-between mb-5">
        <h1 class="text-2xl font-semibold">All Discussions</h1>
        <Button v-if="!this.$readOnlyMode" iconLeft="plus" :route="{ name: 'ProjectDetailDiscussionNew' }">
          New Discussion
        </Button>
      </div>
      <DiscussionList
        :filters="{ project: project.doc.name }"
        routeName="ProjectDetailDiscussion"
      />
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionView from '@/components/DiscussionView.vue'

export default {
  name: 'ProjectDetailDiscussions',
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
