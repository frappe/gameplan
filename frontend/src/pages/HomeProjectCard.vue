<template>
  <router-link
    class="group block rounded-lg border border-gray-100 p-4 shadow-sm hover:bg-gray-100"
    :to="{
      name: 'Project',
      params: { projectId: project.name, teamId: project.team },
    }"
  >
    <div class="flex items-center gap-2">
      <span class="text-xl">{{ project.icon }}</span>

      <span
        class="text-ellipsis whitespace-nowrap text-xl font-medium text-gray-900"
      >
        {{ project.project_title }}
      </span>
      <Tooltip
        v-if="project.unreadCount"
        :text="`${project.unreadCount} unread posts`"
      >
        <span
          class="inline-grid h-5 min-w-[1.25rem] place-items-center rounded-md bg-gray-200 px-1 text-sm text-gray-600"
        >
          {{ project.unreadCount }}
        </span>
      </Tooltip>
      <Tooltip
        v-if="project.comments_count"
        :text="
          project.comments_count === 1
            ? `1 comment in the past week`
            : `${project.comments_count} comments in the past week`
        "
      >
        <div
          class="inline-flex h-5 items-center rounded-md bg-gray-200 px-1 text-sm text-gray-600"
        >
          <FeatherIcon name="bar-chart-2" class="w-4" />
          <span>
            {{ project.comments_count }}
          </span>
        </div>
      </Tooltip>

      <div class="ml-auto">
        <slot name="button" />
      </div>
    </div>
    <div class="mt-2 flex items-end justify-between">
      <span
        class="text-sm font-semibold uppercase tracking-wide text-gray-600/90"
      >
        {{ project.team_title }}
      </span>
      <span class="text-base text-gray-600">
        {{ $dayjs(project.timestamp).fromNow() }}
      </span>
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
