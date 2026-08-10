<template>
  <TabButtons :buttons="spaceTabs" :size="tabButtonSize" v-model="currentTab" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { PillSize } from 'frappe-ui'
import { TabButtons } from 'frappe-ui'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  spaceId: string
}>()

const currentRoute = useRoute()
const router = useRouter()
const isMobileViewport = useIsMobile()

const spaceTabs = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Tasks', value: 'tasks' },
]

const tabButtonSize = computed<PillSize>(() => (isMobileViewport.value ? 'md' : 'sm'))

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
    router.push({
      name: routeName,
      params: { communityId: currentRoute.params.communityId, spaceId: props.spaceId },
    })
  },
})
</script>
