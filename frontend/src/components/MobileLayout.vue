<template>
  <div class="flex h-full flex-col">
    <div class="h-full overflow-auto bg-surface-white" id="scrollContainer">
      <slot />
    </div>
    <div
      class="grid grid-cols-5 bg-surface-modal border-t border-outline-gray-2 standalone:pb-4"
      :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }"
    >
      <button
        v-for="tab in tabs"
        :key="tab.name"
        class="flex flex-col items-center justify-center py-3 transition active:scale-95"
        @click="onTabClick(tab)"
      >
        <component
          :is="tab.icon"
          class="h-6 w-6"
          :class="[tab.isActive ? 'text-ink-gray-8' : 'text-ink-gray-5']"
        />
      </button>
    </div>
  </div>
</template>
<script>
import { scrollTo } from '@/utils/scrollContainer'
import LucideHome from '~icons/lucide/home'
import LucideUsers2 from '~icons/lucide/users-2'
import LucideSearch from '~icons/lucide/search'
import LucideInbox from '~icons/lucide/inbox'
import LucideLayoutGrid from '~icons/lucide/layout-grid'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideNewspaper from '~icons/lucide/newspaper'

export default {
  name: 'MobileLayout',
  computed: {
    tabs() {
      return [
        {
          name: 'Discussions',
          icon: LucideNewspaper,
          route: { name: 'Discussions' },
          isActive: this.$route.name === 'Discussions',
        },
        {
          name: 'MyTasks',
          icon: LucideListTodo,
          route: { name: 'MyTasks' },
          isActive: /MyTasks|Task/g.test(this.$route.name),
        },
        {
          name: 'Spaces',
          icon: LucideLayoutGrid,
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
          icon: LucideUsers2,
          route: { name: 'People' },
          isActive: /People|PersonProfile/g.test(this.$route.name),
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Search',
          icon: LucideSearch,
          route: { name: 'Search' },
          isActive: this.$route.name === 'Search',
          condition: () => this.$user().isNotGuest,
        },
        {
          name: 'Notifications',
          icon: LucideInbox,
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
