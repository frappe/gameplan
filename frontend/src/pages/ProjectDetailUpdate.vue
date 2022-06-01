<template>
  <div class="flex">
    <div class="w-5/12 h-full px-6 py-6 overflow-auto">
      <router-link
        custom
        :to="{ name: 'ProjectDetailUpdate', params: { updateId: 'new' } }"
        v-slot="{ href, navigate }"
      >
        <a
          :href="href"
          @click="navigate"
          class="block p-3 mb-3 border rounded-xl"
          :class="updateId === 'new' ? 'bg-gray-100' : 'hover:bg-gray-50'"
        >
          <div class="flex items-center space-x-4">
            <Avatar :label="$user().full_name" :imageURL="$user().user_image" />
            <div class="text-base text-gray-700">Write an update...</div>
          </div>
        </a>
      </router-link>
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
