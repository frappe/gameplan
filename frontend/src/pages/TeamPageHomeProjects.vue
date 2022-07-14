<template>
  <div>
    <div class="flex items-center justify-between mb-2 space-x-2">
      <h2 class="text-lg text-gray-900">Projects</h2>
      <Button
        v-if="$resources.projects.data?.length"
        iconLeft="plus"
        @click="createNewProjectDialog = true"
      >
        Add Project
      </Button>
    </div>
    <ul role="list" class="grid grid-cols-3 gap-4">
      <li
        v-for="project in $resources.projects.data"
        :key="project.name"
        class="flow-root"
      >
        <div
          class="relative flex items-center p-2 space-x-4 transition-colors border border-gray-100 rounded-xl group hover:bg-gray-100 focus-within:ring-2 focus-within:ring-blue-500"
        >
          <div
            class="flex items-center justify-center flex-shrink-0 w-10 h-10 transition-colors bg-gray-100 rounded-lg group-hover:bg-white"
          >
            <span class="text-4xl">{{ project.icon }}</span>
          </div>
          <div>
            <h3 class="text-lg font-medium text-gray-900">
              <router-link
                :to="{
                  name: 'ProjectDetailOverview',
                  params: { projectId: project.name },
                }"
                class="focus:outline-none"
              >
                <span class="absolute inset-0" aria-hidden="true" />
                {{ project.title }}
              </router-link>
            </h3>
            <p class="mt-1 text-base text-gray-500">
              Updated {{ $dayjs(project.modified).fromNow() }}
            </p>
          </div>
        </div>
      </li>
      <button
        v-if="$resources.projects.data?.length === 0"
        class="relative flex items-center p-2 space-x-4 text-left transition-colors border border-gray-100 rounded-xl group hover:bg-gray-100 focus-within:ring-2 focus-within:ring-blue-500"
        @click="createNewProjectDialog = true"
      >
        <div
          class="flex items-center justify-center flex-shrink-0 w-10 h-10 transition-colors bg-gray-100 rounded-lg group-hover:bg-white"
        >
          <FeatherIcon name="plus" class="w-5 text-gray-600" />
        </div>
        <div>
          <h3 class="text-lg font-medium text-gray-900">New Project</h3>
        </div>
      </button>
    </ul>
    <div
      class="flex flex-col items-center justify-center py-8 bg-gray-100 rounded-xl"
      v-if="0 && $resources.projects.data?.length === 0"
    >
      <FeatherIcon name="folder-plus" class="w-6 h-6 text-gray-500" />
      <span class="mt-2 text-base text-gray-800"> No projects </span>
    </div>
    <Dialog
      :options="{ title: 'Create Project' }"
      v-model="createNewProjectDialog"
    >
      <template #body-content>
        <Input
          type="text"
          label="Project Title"
          v-model="newProjectTitle"
          @keydown.enter="(e) => createProject(e.target.value)"
        />
        <ErrorMessage
          class="mt-2"
          :message="$resources.projects.insert.error"
        />
      </template>
      <template #actions>
        <Button
          appearance="primary"
          @click="createProject(newProjectTitle)"
          :loading="$resources.projects.insert.loading"
        >
          Create
        </Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import { Dialog } from 'frappe-ui'
export default {
  name: 'TeamPageHomeProjects',
  props: ['team'],
  components: {
    Dialog,
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
        type: 'list',
        doctype: 'Team Project',
        filters: { team: this.team.name },
        fields: ['*'],
        order_by: 'modified desc',
        cache: ['Team Projects', this.team.name],
      }
    },
  },
  methods: {
    createProject(title) {
      this.$resources.projects.insert.submit(
        {
          team: this.team.name,
          title,
          sections: [
            { title: 'To Do', type: 'Draft' },
            { title: 'In Progress', type: 'Draft' },
            { title: 'Done', type: 'Closed' },
          ],
        },
        {
          onSuccess(project) {
            this.$resources.projects.reload()
            this.newProjectTitle = ''
            this.createNewProjectDialog = false
            this.$router.push({
              name: 'ProjectDetailOverview',
              params: { projectId: project.name },
            })
          },
        }
      )
    },
  },
}
</script>
