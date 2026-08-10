<template>
  <div>
    <PageHeaderMobile class="sm:hidden" :title="taskTitle">
      <template #prefix>
        <PageHeaderBackButton :to="backRoute" />
      </template>
    </PageHeaderMobile>
    <PageHeader class="hidden sm:flex">
      <SpaceBreadcrumbs
        v-if="space"
        :spaceId="space.name"
        :items="[
          {
            label: 'Tasks',
            route: {
              name: 'SpaceTasks',
              params: { communityId: space?.team, spaceId: space?.name },
            },
          },
          {
            label: task.doc ? task.doc.title : route.params.taskId.toString(),
            route: {
              name: 'SpaceTask',
              params: { communityId: space?.team, spaceId: space?.name, taskId: props.taskId },
            },
          },
        ]"
      />
      <Breadcrumbs
        v-else
        class="h-7"
        :items="[
          {
            label: 'My Tasks',
            route: { name: 'MyTasks' },
          },
          {
            label: task.doc ? task.doc.title : route.params.taskId.toString(),
            route: { name: 'Task', params: { taskId: props.taskId } },
          },
        ]"
      />
    </PageHeader>
    <div>
      <TaskDetail
        :task-id="taskId"
        :read-only-mode="Boolean(space?.archived_at) || $readOnlyMode"
      />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, type RouteLocationRaw } from 'vue-router'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  usePageMeta,
} from 'frappe-ui'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import TaskDetail from '@/components/TaskDetail.vue'
import { useTask } from '@/data/tasks'
import { useSpace } from '@/data/spaces'

const props = defineProps<{
  communityId?: string
  spaceId?: string
  taskId: string
}>()
const task = useTask(() => props.taskId)
const space = useSpace(() => task.doc?.project || props.spaceId)
const route = useRoute()

const taskTitle = computed(() => task.doc?.title || 'Task')
const backRoute = computed<RouteLocationRaw>(() => {
  const spaceId = space.value?.name || props.spaceId
  const communityId = space.value?.team || props.communityId

  if (spaceId && communityId) {
    return {
      name: 'SpaceTasks',
      params: { communityId, spaceId },
    }
  }

  return { name: 'MyTasks' }
})

usePageMeta(() => {
  return {
    title: `${task.doc?.title} | ${space.value?.title || 'My Tasks'}`,
  }
})
</script>
