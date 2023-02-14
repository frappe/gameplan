<template>
  <div class="mt-6 space-y-4">
    <div>
      <div class="mb-5 flex items-center justify-between space-x-2">
        <h2 class="text-2xl font-semibold text-gray-900">Projects</h2>
        <div class="flex items-stretch space-x-2">
          <TabButtons
            :buttons="[{ label: 'Active' }, { label: 'Archived' }]"
            v-model="activeTab"
          />
          <Button
            v-if="teamProjects.length"
            iconLeft="plus"
            @click="createNewProjectDialog = true"
          >
            Add Project
          </Button>
        </div>
      </div>
      <ul role="list" class="grid grid-cols-1 sm:grid-cols-3 sm:gap-4">
        <li
          v-for="project in projectsList"
          :key="project.name"
          class="flow-root"
        >
          <div
            class="group relative flex items-center space-x-4 border-b border-gray-100 py-2 transition-colors focus-within:ring-2 focus-within:ring-blue-500 hover:bg-gray-100 sm:rounded-xl sm:border sm:px-2"
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
                    name: 'Project',
                    params: { projectId: project.name },
                  }"
                  class="focus:outline-none"
                >
                  <span class="absolute inset-0" aria-hidden="true" />
                  <span class="inline-flex items-center">
                    {{ project.title }}
                    <FeatherIcon
                      v-if="project.is_private"
                      name="lock"
                      class="ml-1 h-3 w-3"
                    />
                  </span>
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
            <h3 class="text-lg font-medium text-gray-900">Add Project</h3>
          </div>
        </button>
      </ul>
      <Dialog
        :options="{ title: 'Create Project' }"
        v-model="createNewProjectDialog"
      >
        <template #body-content>
          <div class="space-y-2">
            <Input
              type="text"
              label="Title"
              v-model="newProject.title"
              @input="newProject.title = $event"
              @keydown.enter="createProject"
            />
            <Input
              v-if="!team.doc.is_private"
              type="select"
              label="Visibility"
              :options="[
                { label: 'Visible to everyone', value: 0 },
                { label: 'Visible to team members (Private)', value: 1 },
              ]"
              v-model="newProject.is_private"
            />
            <ErrorMessage :message="projects.insert.error" />
          </div>
        </template>
        <template #actions>
          <Button
            appearance="primary"
            @click="createProject"
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
import TabButtons from '@/components/TabButtons.vue'

export default {
  name: 'TeamProjects',
  props: ['team'],
  components: {
    Dialog,
    TabButtons,
  },
  data() {
    return {
      createNewProjectDialog: false,
      newProject: { title: '', is_private: false },
      activeTab: 'Active',
    }
  },
  computed: {
    projects() {
      return projects
    },
    projectsList() {
      return this.activeTab === 'Active'
        ? this.activeProjects
        : this.archivedProjects
    },
    activeProjects() {
      return this.teamProjects.filter((project) => !project.archived_at)
    },
    archivedProjects() {
      return this.teamProjects.filter((project) => project.archived_at)
    },
    teamProjects() {
      return getTeamProjects(this.team.name)
    },
  },
  methods: {
    createProject() {
      projects.insert.submit(
        {
          team: this.team.name,
          ...this.newProject,
        },
        {
          onSuccess: (project) => {
            projects.reload()
            this.newProject = this.$options.data().newProject
            this.createNewProjectDialog = false
            this.$router.push({
              name: 'Project',
              params: { projectId: project.name },
            })
          },
        }
      )
    },
  },
}
</script>
