<template>
  <div class="mt-6 space-y-4">
    <div>
      <div class="mb-2 flex items-center justify-between space-x-2">
        <h2 class="text-lg text-gray-900">Projects</h2>
        <Button
          v-if="teamProjects.length"
          iconLeft="plus"
          @click="createNewProjectDialog = true"
        >
          Add Project
        </Button>
      </div>
      <ul role="list" class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <li
          v-for="project in teamProjects"
          :key="project.name"
          class="flow-root"
        >
          <div
            class="group relative flex items-center space-x-4 rounded-xl border border-gray-100 p-2 transition-colors focus-within:ring-2 focus-within:ring-blue-500 hover:bg-gray-100"
          >
            <div
              class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 transition-colors group-hover:bg-white"
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
          v-if="teamProjects.length === 0"
          class="group relative flex items-center space-x-4 rounded-xl border border-gray-100 p-2 text-left transition-colors focus-within:ring-2 focus-within:ring-blue-500 hover:bg-gray-100"
          @click="createNewProjectDialog = true"
        >
          <div
            class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 transition-colors group-hover:bg-white"
          >
            <FeatherIcon name="plus" class="w-5 text-gray-600" />
          </div>
          <div>
            <h3 class="text-lg font-medium text-gray-900">New Project</h3>
          </div>
        </button>
      </ul>
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
          <ErrorMessage class="mt-2" :message="projects.insert.error" />
        </template>
        <template #actions>
          <Button
            appearance="primary"
            @click="createProject(newProjectTitle)"
            :loading="projects.insert.loading"
          >
            Create
          </Button>
        </template>
      </Dialog>
    </div>
  </div>
</template>
<script>
import { Dialog } from 'frappe-ui'
import { projects, getTeamProjects } from '@/data/projects'

export default {
  name: 'TeamProjects',
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
  computed: {
    projects() {
      return projects
    },
    teamProjects() {
      return getTeamProjects(this.team.name)
    },
  },
  methods: {
    createProject(title) {
      projects.insert.submit(
        {
          team: this.team.name,
          title,
        },
        {
          onSuccess: (project) => {
            projects.reload()
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
