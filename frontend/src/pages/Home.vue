<template>
  <div class="flex flex-col h-full">
    <header
      class="sticky top-0 z-10 flex items-center h-12 px-4 py-3 bg-white border-b"
    >
      <Breadcrumbs
        :breadcrumbs="[
          {
            title: 'Home',
            icon: '🏠',
          },
        ]"
      />
    </header>
    <div class="flex flex-1 min-h-0">
      <div class="w-5/12 h-full px-6 py-6 overflow-auto">
        <ProjectStatusUpdates routeName="Home" />
      </div>
      <div class="w-7/12 overflow-auto border-l">
        <ProjectStatusUpdatesView :updateId="updateId" />
      </div>
    </div>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ProjectStatusUpdates from '@/components/ProjectStatusUpdates.vue'
import ProjectStatusUpdatesView from '@/components/ProjectStatusUpdatesView.vue'
export default {
  name: 'Home',
  props: ['updateId'],
  components: { Breadcrumbs, ProjectStatusUpdates, ProjectStatusUpdatesView },
  pageMeta() {
    return {
      title: 'Home',
      emoji: '🏠',
    }
  },
}
</script>
