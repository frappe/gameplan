<template>
  <!-- Shown only while the deprecated Tasks and Pages are switched on in GP Settings. -->
  <TabButtons
    v-if="tasksAndPagesEnabled"
    :options="spaceTabs"
    :size="tabButtonSize"
    v-model="currentTab"
  />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { TabsSize } from 'frappe-ui'
import { TabButtons } from 'frappe-ui'
import { tasksAndPagesEnabled } from '@/data/tasksAndPages'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  spaceId: string
}>()

type SpaceTab = 'discussions' | 'pages' | 'tasks'

const route = useRoute()
const router = useRouter()
const isMobileViewport = useIsMobile()

const spaceTabs: Array<{ label: string; value: SpaceTab }> = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Tasks', value: 'tasks' },
]

const routeNames: Record<SpaceTab, string> = {
  discussions: 'SpaceDiscussions',
  pages: 'SpacePages',
  tasks: 'SpaceTasks',
}

const tabButtonSize = computed<TabsSize>(() => (isMobileViewport.value ? 'md' : 'sm'))

const currentTab = computed({
  get(): SpaceTab {
    if (route.name === 'SpacePages') return 'pages'
    if (route.name === 'SpaceTasks') return 'tasks'
    return 'discussions'
  },
  set(value: string | number | undefined) {
    const tab = spaceTabs.find((option) => option.value === value)
    if (!tab || tab.value === currentTab.value) return
    router.push({
      name: routeNames[tab.value],
      params: { communityId: route.params.communityId, spaceId: props.spaceId },
    })
  },
})
</script>
