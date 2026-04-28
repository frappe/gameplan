<template>
  <div class="fixed inset-0 flex flex-col overflow-hidden touch-none">
    <div
      class="flex-1 overflow-y-auto overscroll-auto bg-surface-white [-webkit-overflow-scrolling:touch]"
      id="scrollContainer"
    >
      <slot />
    </div>
    <div
      class="grid grid-cols-5 shrink-0 bg-surface-modal border-t border-outline-gray-2 standalone:pb-4"
      :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }"
      v-if="!isNewCommentOpen"
    >
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="flex flex-col items-center justify-center py-3 transition active:scale-95"
        @click="onTabClick(tab)"
      >
        <span
          :class="[tab.icon, 'h-6 w-6', tab.isActive ? 'text-ink-gray-8' : 'text-ink-gray-5']"
        />
      </button>
    </div>
  </div>
</template>
<script>
import { scrollTo } from '@/utils/scrollContainer'
import { isNewCommentOpen as isNewCommentOpenRef } from '@/data/newComment'
export default {
  name: 'MobileLayout',
  computed: {
    isNewCommentOpen() {
      return isNewCommentOpenRef.value
    },
    tabs() {
      return [
        {
          name: 'Discussions',
          icon: 'lucide-newspaper',
          route: { name: 'Discussions' },
          isActive: this.$route.name === 'Discussions',
        },
        {
          name: 'MyTasks',
          icon: 'lucide-list-todo',
          route: { name: 'MyTasks' },
          isActive: /MyTasks|Task/g.test(this.$route.name),
        },
        {
          name: 'Spaces',
          icon: 'lucide-layout-grid',
          route: { name: 'Spaces' },
          isActive: [
            'Spaces',
            'Space',
            'SpaceDiscussions',
            'SpaceDiscussion',
            'SpaceTasks',
            'SpaceTask',
          ].includes(this.$route.name),
        },
        {
          name: 'People',
          icon: 'lucide-users-2',
          route: { name: 'People' },
          isActive: /People|PersonProfile/g.test(this.$route.name),
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Search',
          icon: 'lucide-search',
          route: { name: 'Search' },
          isActive: this.$route.name === 'Search',
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Notifications',
          icon: 'lucide-inbox',
          route: { name: 'Notifications' },
          isActive: this.$route.name === 'Notifications',
        },
      ].filter((tab) => (tab.condition ? tab.condition() : true))
    },
  },
  methods: {
    onTabClick(tab) {
      if (tab.isActive) {
        scrollTo({ top: 0, behavior: 'smooth' })
        return
      }
      this.$router.push(tab.route)
    },
  },
}
</script>
