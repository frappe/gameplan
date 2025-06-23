<template>
  <div class="mt-6">
    <ReadmeEditor
      :resource="team"
      fieldname="readme"
      :border="true"
      :collapsible="true"
      :editable="!team.doc.archived_at"
    />

    <div class="mt-8">
      <div class="mb-5 flex items-center justify-between space-x-2">
        <h2 class="text-2xl font-semibold text-ink-gray-8">Projects</h2>
        <div class="flex items-stretch space-x-2">
          <TabButtons :buttons="[{ label: 'Active' }, { label: 'Archived' }]" v-model="activeTab" />
          <Button v-if="teamProjects.length" @click="createNewProjectDialog = true" variant="solid">
            <template #prefix>
              <LucidePlus class="h-4 w-4" />
            </template>
            Add Project
          </Button>
        </div>
      </div>
      <ul role="list" class="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <li v-for="project in projectsList" :key="project.name" class="flow-root">
          <div
            class="group relative items-center rounded-lg p-3 shadow transition-colors focus-within:ring focus-within:ring-outline-gray-2 hover:bg-surface-gray-2"
          >
            <div>
              <h3 class="overflow-hidden text-lg font-medium text-ink-gray-8">
                <router-link
                  :to="{
                    name: 'Project',
                    params: { projectId: project.name },
                  }"
                  class="inline-flex w-full overflow-hidden text-ellipsis whitespace-nowrap focus:outline-none"
                >
                  <span class="absolute inset-0" aria-hidden="true" />
                  <span class="inline-flex items-center">
                    {{ project.title }}
                    <LucideLock v-if="project.is_private" class="ml-1 h-3 w-3" />
                  </span>
                </router-link>
              </h3>
              <p class="mt-1 text-base">
                <template v-if="project.tasks_count">
                  <span class="text-ink-gray-8">
                    {{ project.tasks_count }}
                  </span>
                  <span class="text-ink-gray-6"
                    >&nbsp;{{ project.tasks_count === 1 ? 'task' : 'tasks' }}
                  </span>
                  &middot;
                </template>
                <template v-if="project.discussions_count">
                  <span class="text-ink-gray-8">
                    {{ project.discussions_count }}
                  </span>
                  <span class="text-ink-gray-6"
                    >&nbsp;{{ project.discussions_count === 1 ? 'discussion' : 'discussions' }}
                  </span>
                </template>
                <span
                  class="text-ink-gray-6"
                  v-if="project.tasks_count + project.discussions_count == 0"
                >
                  {{ dayjsLocal(project.creation).fromNow() }}
                </span>
              </p>
            </div>
          </div>
        </li>
        <button
          v-if="teamProjects.length === 0"
          class="group relative flex items-center space-x-4 rounded-xl border border-gray-100 p-2 text-left transition-colors focus-within:ring-2 focus-within:ring-blue-500 hover:bg-surface-gray-2"
          @click="createNewProjectDialog = true"
        >
          <div
            class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-surface-gray-2 transition-colors group-hover:bg-surface-white"
          >
            <LucidePlus class="w-5 text-ink-gray-5" />
          </div>
          <div>
            <h3 class="text-lg font-medium text-ink-gray-8">Add Project</h3>
          </div>
        </button>
      </ul>
      <Dialog :options="{ title: 'Create project' }" v-model="createNewProjectDialog">
        <template #body-content>
          <div class="space-y-5">
            <FormControl label="Title" v-model="newProject.title" @keydown.enter="createProject" />
            <FormControl
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
            size="md"
            class="w-full"
            variant="solid"
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
import { Dialog, FormControl, TextInput, TabButtons, dayjsLocal } from 'frappe-ui'
import { projects, getTeamProjects, getTeamArchivedProjects } from '@/data/projects'

export default {
  name: 'TeamOverview',
  props: ['team'],
  components: {
    Dialog,
    TabButtons,
    TextInput,
    FormControl,
  },
  setup() {
    return {
      dayjsLocal,
    }
  },
  data() {
    return {
      createNewProjectDialog: false,
      newProject: { title: '', is_private: 0 },
      activeTab: 'Active',
    }
  },
  computed: {
    projects() {
      return projects
    },
    projectsList() {
      return this.activeTab === 'Active' ? this.activeProjects : this.archivedProjects
    },
    activeProjects() {
      return this.teamProjects.filter((project) => !project.archived_at)
    },
    archivedProjects() {
      return getTeamArchivedProjects(this.team.name)
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
        },
      )
    },
  },
}
</script>
