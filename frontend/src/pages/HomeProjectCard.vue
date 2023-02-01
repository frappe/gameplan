<template>
  <router-link
    class="group flex items-center rounded-xl border border-gray-100 p-2 hover:bg-gray-100"
    :to="{
      name: 'Project',
      params: { projectId: project.name, teamId: project.team },
    }"
  >
    <div
      class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md bg-gray-100 text-xl group-hover:bg-white"
    >
      <span class="text-4xl group-hover:hidden">{{ project.icon }}</span>
      <div class="hidden group-hover:block">
        <slot name="button" />
      </div>
    </div>
    <div class="ml-4 flex-1">
      <div class="flex items-center justify-between">
        <span class="text-lg font-medium text-gray-900">
          {{ project.project_title }}
        </span>
        <Tooltip
          class="flex"
          v-if="project.unreadCount"
          :text="`${project.unreadCount} unread posts`"
        >
          <span
            class="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-gray-200 px-1.5 text-sm text-gray-600"
          >
            {{ project.unreadCount }}
          </span>
        </Tooltip>
      </div>
      <div class="mt-1 flex items-end justify-between leading-none">
        <span class="text-base tracking-wide text-gray-500">
          {{ project.team_title }}
        </span>
        <Tooltip
          class="flex"
          v-if="project.comments_count"
          :text="
            project.comments_count === 1
              ? `1 comment in the past week`
              : `${project.comments_count} comments in the past week`
          "
        >
          <div
            class="inline-flex items-center rounded-md text-sm text-gray-600"
          >
            <FeatherIcon name="bar-chart-2" class="h-4 w-4" />
            <div class="-mb-[3px]">
              {{ project.comments_count }}
            </div>
          </div>
        </Tooltip>
        <span v-else class="text-sm text-gray-500">
          {{ $dayjs(project.timestamp).fromNow(true) }}
        </span>
      </div>
    </div>
  </router-link>
</template>
<script>
import { Tooltip } from 'frappe-ui'

export default {
  name: 'HomescreenProjectCard',
  props: {
    project: {
      type: Object,
    },
  },
  components: { Tooltip },
}
</script>
