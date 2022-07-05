<template>
  <div class="flex">
    <div class="w-5/12 h-full px-6 py-6 overflow-auto">
      <div class="flex items-center justify-between mb-5">
        <h1 class="text-2xl font-semibold">All Discussions</h1>
        <Button
          iconLeft="plus"
          :route="{ name: 'ProjectDetailUpdate', params: { postId: 'new' } }"
        >
          New Discussion
        </Button>
      </div>
      <DiscussionList
        :filters="{ project: project.doc.name }"
        routeName="ProjectDetailUpdate"
      />
    </div>
    <div class="w-7/12 overflow-auto border-l">
      <ProjectDetailUpdateNew v-if="postId == 'new'" :project="project" />
      <DiscussionView v-else :postId="postId" />
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionView from '@/components/DiscussionView.vue'
import ProjectDetailUpdateNew from './ProjectDetailUpdateNew.vue'

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
    ProjectDetailUpdateNew,
  },
  methods: {
    isActive(update) {
      return this.$route.params.postId === update.name
    },
  },
}
</script>
