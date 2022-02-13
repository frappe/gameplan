<template>
  <div class="pb-40" v-if="$resources.project.data">
    <div class="container py-8 mx-auto">
      <div>
        <div class="flex items-center space-x-2">
          <div class="flex items-center space-x-2">
            <ProjectIconPicker
              ref="projectIconPicker"
              v-model="project.icon"
              @update:modelValue="
                (icon) =>
                  $resources.updateProject.submit({
                    doctype: 'Team Project',
                    name: project.name,
                    fieldname: {
                      icon,
                    },
                  })
              "
            />
            <h1
              class="text-6xl font-bold"
              :title="`${Math.round(project.progress)}% complete`"
            >
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
import ProjectIconPicker from '@/components/ProjectIconPicker.vue'

export default {
  name: 'ProjectDetail',
  props: ['team', 'projectId'],
  components: {
    Dropdown,
    Spinner,
    Pie,
    ProjectDetailTasks,
    ProjectIconPicker,
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
          if (!project.icon) {
            this.$nextTick(() => this.$refs.projectIconPicker.setRandom())
          }
          project.task_states.map((task_state) => {
            task_state.open = true
          })
        },
      }
    },
    updateProject() {
      return {
        method: 'frappe.client.set_value',
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
