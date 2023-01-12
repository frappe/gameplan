<template>
  <div class="flex">
    <div class="h-full w-full overflow-auto py-6">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="text-2xl font-semibold">Tasks</h2>
        <div class="flex items-stretch space-x-2">
          <div class="flex rounded-md bg-gray-100 p-1 text-sm">
            <button
              class="rounded px-2 py-1 leading-none transition-all"
              :class="{ 'bg-white shadow': openTasks }"
              @click="
                $router.replace({
                  name: 'ProjectTasks',
                  query: {
                    open: true,
                  },
                  params: {
                    teamId: project.doc.team,
                    projectId: project.doc.name,
                  },
                })
              "
            >
              Open
            </button>
            <button
              class="rounded px-2 py-1 leading-none transition-all"
              :class="{ 'bg-white shadow': !openTasks }"
              @click="
                $router.replace({
                  name: 'ProjectTasks',
                  query: {
                    open: false,
                  },
                  params: {
                    teamId: project.doc.team,
                    projectId: project.doc.name,
                  },
                })
              "
            >
              Closed
            </button>
          </div>
          <Button
            iconLeft="plus"
            :route="{ name: 'ProjectTaskNew' }"
            v-if="!$readOnlyMode && !project.doc.archived_at"
          >
            New Task
          </Button>
        </div>
      </div>
      <div class="divide-y">
        <router-link
          v-for="d in tasks.data"
          :key="d.name"
          :to="{
            name: 'ProjectTaskDetail',
            params: { teamId: d.team, projectId: d.project, taskId: d.name },
          }"
          class="block p-3 hover:bg-gray-50"
        >
          <div class="flex items-center justify-between">
            <span class="text-lg font-medium">
              {{ d.title }}
            </span>
            <div class="flex items-center space-x-2 text-base">
              <Tooltip
                v-if="d.assigned_to"
                placement="bottom"
                :text="`Assigned to ${$user(d.assigned_to).full_name}`"
              >
                <UserAvatar size="sm" :user="d.assigned_to" />
              </Tooltip>
            </div>
          </div>
          <div
            class="mt-0.5 flex items-center justify-between text-sm text-gray-600"
          >
            <span :title="taskTimestampDescription(d)">
              Created by {{ $user(d.owner).full_name }}
              {{
                $dayjs().diff(d.creation, 'month') >= 9
                  ? 'on ' + $dayjs(d.creation).format('D MMM YYYY')
                  : $dayjs(d.creation).fromNow()
              }}
            </span>
            <span
              :class="{
                'text-red-600': $dayjs().isAfter($dayjs(d.due_date), 'day'),
              }"
              v-if="d.due_date"
            >
              {{ $dayjs(d.due_date).format('LL') }}
            </span>
          </div>
        </router-link>
      </div>
      <div
        class="text-base text-gray-600"
        v-if="!tasks.loading && !tasks.data?.length"
      >
        No tasks
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Popover, Tooltip } from 'frappe-ui'
import TabButtons from '@/components/TabButtons.vue'

export default {
  name: 'ProjectTasks',
  props: ['project'],
  resources: {
    openTasks() {
      if (!this.openTasks) return
      return {
        type: 'list',
        cache: ['Project Tasks', this.project.doc.name, 'open'],
        doctype: 'GP Task',
        fields: ['*'],
        filters: {
          project: this.project.doc.name,
          is_completed: false,
        },
        orderBy: 'creation desc',
        auto: true,
      }
    },
    closedTasks() {
      if (this.openTasks) return
      return {
        type: 'list',
        cache: ['Project Tasks', this.project.doc.name, 'closed'],
        doctype: 'GP Task',
        fields: ['*'],
        filters: {
          project: this.project.doc.name,
          is_completed: true,
        },
        orderBy: 'creation desc',
        auto: true,
      }
    },
  },
  methods: {
    taskTimestampDescription(d) {
      return [
        `Created On: ${this.$dayjs(d.creation).format('LLL')}`,
        `Updated On: ${this.$dayjs(d.modified).format('LLL')}`,
      ].join('\n')
    },
  },
  computed: {
    tasks() {
      if (this.openTasks) {
        return this.$resources.openTasks
      } else {
        return this.$resources.closedTasks
      }
    },
    openTasks() {
      return this.$route.query.open === 'true'
    },
  },
  components: { Avatar, Popover, Tooltip, TabButtons },
}
</script>
