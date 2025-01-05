<template>
  <TabButtons :buttons="spaceTabs" v-model="currentTab" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TabButtons } from 'frappe-ui'

const props = defineProps<{
  spaceId: string
}>()

const currentRoute = useRoute()
const router = useRouter()

const spaceTabs = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Tasks', value: 'tasks' },
]

const currentTab = computed({
  get() {
    let currentPage = currentRoute.name?.toString() || 'SpaceDiscussions'
    return {
      SpaceDiscussions: 'discussions',
      SpacePages: 'pages',
      SpaceTasks: 'tasks',
    }[currentPage]
  },
  set(value) {
    if (!value) return
    let routeName = {
      discussions: 'SpaceDiscussions',
      pages: 'SpacePages',
      tasks: 'SpaceTasks',
    }[value]
    router.push({ name: routeName, params: { spaceId: props.spaceId } })
  },
})
</script>
