<template>
  <div class="flex">
    <div class="h-full w-full py-6">
      <div class="mb-4.5 flex items-center justify-between">
        <h2 class="text-xl font-semibold">Discussions</h2>
        <Button
          variant="solid"
          v-if="!$readOnlyMode && !project.doc.archived_at"
          :route="{ name: 'ProjectDiscussionNew' }"
        >
          <template #prefix>
            <LucidePlus class="h-4 w-4" />
          </template>
          Add new
        </Button>
      </div>
      <DiscussionList
        class="-mx-5 sm:mx-0"
        :listOptions="{ filters: { project: project.doc.name } }"
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
