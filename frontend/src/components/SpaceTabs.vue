<template>
  <Select class="min-w-32" v-if="screen.width < 640" :options="spaceTabs" v-model="currentTab" />
  <TabButtons v-else :buttons="spaceTabs" v-model="currentTab" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TabButtons, Select } from 'frappe-ui'
import { useScreenSize } from '@/utils/composables'

const props = defineProps<{
  spaceId: string
}>()

const currentRoute = useRoute()
const router = useRouter()
const screen = useScreenSize()

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
