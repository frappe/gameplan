<template>
  <div class="flex">
    <div class="w-full h-full py-6 overflow-auto">
      <div class="flex items-center justify-between mb-5">
        <h1 class="text-2xl font-semibold">Tasks</h1>
        <div class="flex items-stretch space-x-2">
          <div class="flex p-1 text-sm bg-gray-100 rounded-md">
            <button
              class="px-2 py-1 leading-none transition-all rounded"
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
              class="px-2 py-1 leading-none transition-all rounded"
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
          <Button iconLeft="plus" :route="{ name: 'ProjectTaskNew' }">
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
                <Avatar
                  size="sm"
                  :label="$user(d.assigned_to).full_name"
                  :imageURL="$user(d.assigned_to).user_image"
                />
              </Tooltip>
            </div>
          </div>
          <div
            class="text-gray-600 flex items-center justify-between mt-0.5 text-sm"
          >
            <span>
              Created by {{ $user(d.owner).full_name }}
              {{
                $dayjs().diff(d.creation, 'month') >= 9
                  ? 'on ' + $dayjs(d.creation).format('D MMM YYYY')
                  : $dayjs(d.creation).fromNow()
              }}
            </span>
            <span :title="taskTimestampDescription(d)">
              {{
                $dayjs().diff(d.modified, 'day') >= 25
                  ? $dayjs(d.modified).format('D MMM')
                  : $dayjs(d.modified).fromNow(true)
              }}
            </span>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Popover, Tooltip } from 'frappe-ui'

export default {
  name: 'ProjectTasks',
  props: ['project'],
  resources: {
    openTasks() {
      if (!this.openTasks) return
      return {
        type: 'list',
        cache: ['Project Tasks', this.project.doc.name, 'open'],
        doctype: 'Team Task',
        fields: ['*'],
        filters: {
          project: this.project.doc.name,
          is_completed: false,
        },
        order_by: 'creation desc',
      }
    },
    closedTasks() {
      if (this.openTasks) return
      return {
        type: 'list',
        cache: ['Project Tasks', this.project.doc.name, 'closed'],
        doctype: 'Team Task',
        fields: ['*'],
        filters: {
          project: this.project.doc.name,
          is_completed: true,
        },
        order_by: 'creation desc',
      }
    },
  },
  methods: {
    taskTimestampDescription(d) {
      return [
        `Created On: ${this.$dayjs(d.creation)}`,
        `Updated On: ${this.$dayjs(d.modified)}`,
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
  components: { Avatar, Popover, Tooltip },
}
</script>
