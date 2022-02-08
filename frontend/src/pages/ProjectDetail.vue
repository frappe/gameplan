<template>
  <div class="pb-40" v-if="$resources.project.data">
    <div class="container py-8 mx-auto">
      <div>
        <div class="flex items-center space-x-2">
          <div
            class="flex items-center space-x-2"
            :title="`${Math.round(project.progress)}% complete`"
          >
            <Pie
              class="w-6"
              :value="project.progress"
              :key="project.progress"
            />
            <h1 class="text-6xl font-bold">
              {{ project.title }}
            </h1>
          </div>
          <Dropdown
            placement="left"
            :button="{ icon: 'more-horizontal', appearance: 'minimal' }"
            :options="[
              {
                group: 'Details',
                hideLabel: true,
                items: [
                  {
                    label: 'Edit Description',
                    icon: 'edit',
                  },
                  {
                    label: 'Invite Team Members',
                    icon: 'mail',
                  },
                ],
              },
              {
                group: 'Actions',
                hideLabel: true,
                items: [
                  {
                    label: 'Delete',
                    icon: 'trash-2',
                  },
                ],
              },
            ]"
          />
        </div>
        <p class="text-sm text-gray-500">
          created {{ $dayjs(project.creation).fromNow() }}
        </p>
      </div>
    </div>

    <ProjectDetailTasks v-if="project" :project="project" />
  </div>
</template>
<script>
import { Dropdown, Spinner } from 'frappe-ui'
import Pie from '@/components/Pie.vue'
import ProjectDetailTasks from './ProjectDetailTasks.vue'

export default {
  name: 'ProjectDetail',
  props: ['team', 'projectId'],
  components: {
    Dropdown,
    Spinner,
    Pie,
    ProjectDetailTasks,
  },
  resources: {
    project() {
      return {
        method: 'frappe.client.get',
        cache: ['team-project', this.projectId],
        params: {
          doctype: 'Team Project',
          name: this.projectId,
        },
        auto: true,
        onSuccess(project) {
          project.task_states.map((task_state) => {
            task_state.open = true
          })
        },
      }
    },
  },
  computed: {
    project() {
      return this.$resources.project.data
    },
  },
}
</script>
