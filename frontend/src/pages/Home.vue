<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="breadcrumbs" />
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
import { Breadcrumbs, getCachedDocumentResource, usePageMeta } from 'frappe-ui'

let breadcrumbs = computed(() => {
  let route = useRoute()
  let items = [{ label: 'Home', route: { name: 'Home' } }]
  if (route.name === 'Discussions') {
    items.push({
      label: 'Discussions',
      route: { name: 'Discussions' },
    })
  }
  if (['MyTasks', 'Task'].includes(route.name)) {
    items.push({
      label: 'My Tasks',
      route: { name: 'MyTasks' },
    })
  }
  if (route.name === 'Task') {
    let task = getCachedDocumentResource('GP Task', route.params.taskId)
    items.push({
      label: task?.doc ? task.doc.title : route.params.taskId,
      route: { name: 'Task' },
    })
  }
  return items
})

usePageMeta(() => {
  return {
    title: 'Home',
  }
})
</script>
