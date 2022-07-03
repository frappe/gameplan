<template>
  <div class="flex">
    <div class="w-5/12 h-full px-6 py-6 overflow-auto">
      <div class="flex items-center justify-between mb-5">
        <h1 class="text-2xl font-semibold">All Discussions</h1>
        <Button
          iconLeft="plus"
          :route="{ name: 'ProjectDetailUpdate', params: { updateId: 'new' } }"
        >
          New Discussion
        </Button>
      </div>
      <ProjectStatusUpdates
        :filters="{ project: project.doc.name }"
        routeName="ProjectDetailUpdate"
      />
    </div>
    <div class="w-7/12 overflow-auto border-l">
      <ProjectDetailUpdateNew v-if="updateId == 'new'" :project="project" />
      <ProjectStatusUpdatesView v-else :updateId="updateId" />
    </div>
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'
import Link from '@/components/Link.vue'
import Reactions from '@/components/Reactions.vue'
import ProjectStatusUpdates from '@/components/ProjectStatusUpdates.vue'
import ProjectStatusUpdatesView from '@/components/ProjectStatusUpdatesView.vue'
import ProjectDetailUpdateNew from './ProjectDetailUpdateNew.vue'

export default {
  name: 'ProjectDetailUpdate',
  props: ['project', 'updateId'],
  components: {
    TextEditor,
    Avatar,
    Link,
    Reactions,
    ProjectStatusUpdates,
    ProjectStatusUpdatesView,
    ProjectDetailUpdateNew,
  },
  methods: {
    isActive(update) {
      return this.$route.params.updateId === update.name
    },
  },
}
</script>
