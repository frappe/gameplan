<template>
  <div class="flex">
    <div class="h-full w-full py-6">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="text-2xl font-semibold">Posts</h2>
        <Button
          v-if="!$readOnlyMode && !project.doc.archived_at"
          iconLeft="plus"
          :route="{ name: 'ProjectDiscussionNew' }"
        >
          New Discussion
        </Button>
      </div>
      <DiscussionList
        class="-mx-5 sm:mx-0"
        :filters="{ project: project.doc.name }"
        routeName="ProjectDiscussion"
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
  name: 'ProjectDiscussions',
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
