<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
    >
      <PageBreadcrumbs class="h-7" :items="breadcrumbs" />
      <button
        @click="showCommandPalette"
        class="form-input hidden w-full max-w-[20rem] py-0 text-left active:bg-gray-200 md:block"
      >
        <div class="flex items-center">
          <LucideSearch class="w-4 text-gray-600" />
          <span class="ml-2 text-base text-gray-500">
            {{ searchPlaceholder }}
          </span>
        </div>
      </button>
    </header>

    <router-view v-slot="{ Component, route }">
      <div :class="{ 'mx-auto w-full max-w-4xl px-5': !route.meta?.fullWidth }">
        <component :is="Component" />
      </div>
    </router-view>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { getPlatform } from '@/utils'
import { showCommandPalette } from '@/components/CommandPalette.vue'
import { getCachedDocumentResource } from 'frappe-ui'

let breadcrumbs = computed(() => {
  let route = useRoute()
  let items = [{ label: 'Home', route: { name: 'Home' } }]
  if (route.name === 'HomeDiscussions') {
    items.push({
      label: 'Discussions',
      route: { name: 'HomeDiscussions' },
    })
  }
  if (route.name === 'HomeProjects') {
    items.push({
      label: 'Projects',
      route: { name: 'HomeProjects' },
    })
  }
  if (['HomeTasks', 'HomeTask'].includes(route.name)) {
    items.push({
      label: 'My Tasks',
      route: { name: 'HomeTasks' },
    })
  }
  if (route.name === 'HomeTask') {
    let task = getCachedDocumentResource('GP Task', route.params.taskId)
    items.push({
      label: task?.doc ? task.doc.title : route.params.taskId,
      route: { name: 'HomeTask' },
    })
  }
  return items
})

const searchPlaceholder = computed(() => {
  let platform = getPlatform()
  if (platform === 'mac') {
    return 'Jump to project or team (⌘K)'
  }
  return 'Jump to project or team (Ctrl+K)'
})
</script>
