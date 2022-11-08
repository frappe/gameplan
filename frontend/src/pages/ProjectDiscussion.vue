<template>
  <div class="flex" v-if="project">
    <DiscussionView
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(project.doc.archived_at) || $readOnlyMode"
    />
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionView from '@/components/DiscussionView.vue'
import { teams } from '@/data/teams'

export default {
  name: 'ProjectDiscussion',
  props: ['team', 'project', 'teamId', 'projectId', 'postId', 'slug'],
  components: {
    TextEditor,
    Avatar,
    Link,
    Reactions,
    DiscussionList,
    DiscussionView,
  },
  watch: {
    postId: {
      immediate: true,
      handler() {
        for (let team of teams.data || []) {
          if (team.name === this.team.doc.name) {
            team.open = true
          }
        }
      },
    },
  },
  methods: {
    isActive(update) {
      return Number(this.$route.params.postId) === update.name
    },
  },
}
</script>
