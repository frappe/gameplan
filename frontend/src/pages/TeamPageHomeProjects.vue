<template>
  <div>
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold">Projects</h2>
      <Button icon-left="plus" @click="createNewProjectDialog = true">
        New Project
      </Button>
    </div>
    <ul
      role="list"
      class="grid grid-cols-1 gap-4 py-4 mt-4 border-t border-gray-200 empty:py-0 sm:grid-cols-2 lg:grid-cols-3"
    >
      <li
        v-for="project in $resources.projects.data"
        :key="project.name"
        class="flow-root"
      >
        <div
          class="relative flex items-center p-2 -m-2 space-x-4 rounded-xl hover:bg-gray-50 focus-within:ring-2 focus-within:ring-blue-500"
        >
          <div
            class="flex items-center justify-center flex-shrink-0 w-10 h-10 bg-gray-400 rounded-lg"
          >
            <FeatherIcon
              name="menu"
              class="w-4 h-4 text-white"
              aria-hidden="true"
            />
          </div>
          <div>
            <h3 class="text-base font-medium text-gray-900">
              <router-link
                :to="{
                  name: 'ProjectDetail',
                  params: { projectId: project.name },
                }"
                class="focus:outline-none"
              >
                <span class="absolute inset-0" aria-hidden="true" />
                {{ project.title }}<span aria-hidden="true"> &rarr;</span>
              </router-link>
            </h3>
            <p class="mt-1 text-base text-gray-500">
              updated {{ $dayjs(project.modified).fromNow() }}
            </p>
          </div>
        </div>
      </li>
    </ul>
    <div
      class="flex flex-col items-center justify-center py-8"
      v-if="$resources.projects.data?.length === 0"
    >
      <FeatherIcon name="folder-plus" class="w-6 h-6 text-gray-500" />
      <span class="mt-2 text-base text-gray-800"> No projects </span>
    </div>
    <NewDialog
      :options="{ title: 'Create Project' }"
      v-model="createNewProjectDialog"
    >
      <template #dialog-content>
        <Input
          type="text"
          label="Project Title"
          v-model="newProjectTitle"
          @keydown.enter="
            (e) =>
              $resources.createProject.submit({
                doc: {
                  doctype: 'Team Project',
                  team: team.name,
                  title: e.target.value,
                  task_states: [{ status: 'To do' }, { status: 'In progress' }],
                },
              })
          "
        />
        <ErrorMessage class="mt-2" :message="$resources.createProject.error" />
      </template>
      <template #dialog-actions>
        <Button
          type="primary"
          @click="
            $resources.createProject.submit({
              doc: {
                doctype: 'Team Project',
                team: team.name,
                title: newProjectTitle,
                task_states: [{ status: 'To do' }, { status: 'In progress' }],
              },
            })
          "
          :loading="$resources.createProject.loading"
        >
          Create
        </Button>
      </template>
    </NewDialog>
  </div>
</template>
<script>
import { NewDialog } from 'frappe-ui'
export default {
  name: 'TeamPageHomeProjects',
  props: ['team'],
  components: {
    NewDialog,
  },
  data() {
    return {
      createNewProjectDialog: false,
      newProjectTitle: '',
    }
  },
  resources: {
    projects() {
      return {
        method: 'frappe.client.get_list',
        cache: ['team-projects', this.team.name],
        params: {
          doctype: 'Team Project',
          filters: { team: this.team.name },
          fields: ['*'],
          order_by: 'modified desc',
        },
        auto: true,
      }
    },
    createProject: {
      method: 'frappe.client.insert',
      onSuccess(project) {
        this.newProjectTitle = ''
        this.createNewProjectDialog = false
        this.$router.push({
          name: 'ProjectDetail',
          params: { projectId: project.name },
        })
      },
    },
  },
}
</script>
