<template>
  <div class="flex h-full flex-col">
    <div class="h-full overflow-auto" id="scrollContainer">
      <slot />
    </div>
    <div
      class="grid grid-cols-5 border-t border-gray-300 standalone:pb-4"
      :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }"
    >
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="flex flex-col items-center justify-center py-3"
        @click="onTabClick(tab)"
      >
        <FeatherIcon
          :name="tab.icon"
          class="h-6 w-6"
          :class="[tab.isActive ? 'text-blue-600' : 'text-gray-900']"
        />
      </button>
    </div>
  </div>
</template>
<script>
import { scrollTo } from '@/utils/scrollContainer'

export default {
  name: 'MobileLayout',
  computed: {
    tabs() {
      return [
        {
          name: 'Home',
          icon: 'home',
          route: { name: 'Home' },
          isActive: ['Home'].includes(this.$route.name),
        },
        {
          name: 'Teams',
          icon: 'sidebar',
          route: { name: 'Teams' },
          isActive: [
            'Teams',
            'TeamOverview',
            'TeamProjects',
            'ProjectOverview',
            'ProjectDiscussions',
            'ProjectDiscussion',
            'ProjectDiscussionNew',
            'ProjectTasks',
            'ProjectTaskDetail',
          ].includes(this.$route.name),
        },
        {
          name: 'People',
          icon: 'users',
          route: { name: 'People' },
          isActive: /People|PersonProfile/g.test(this.$route.name),
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Search',
          icon: 'search',
          route: { name: 'Search' },
          isActive: this.$route.name === 'Search',
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Notifications',
          icon: 'inbox',
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
