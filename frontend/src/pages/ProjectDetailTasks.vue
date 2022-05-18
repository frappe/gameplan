<template>
  <div class="relative">
    <div>
      <div class="container">
        <div class="flex items-center h-10 text-base text-gray-600 border-b">
          <div class="w-[70%]">Task</div>
          <div class="w-[15%]">Assignee</div>
          <div class="w-[10%]">Due Date</div>
        </div>
      </div>
      <template v-if="!$resources.tasks.data">
        <div class="container py-2 mx-auto text-lg font-semibold text-gray-900">
          <div class="flex items-center -ml-8">
            <Button
              class="mr-1"
              appearance="minimal"
              :icon="'chevron-down'"
              :disabled="true"
            />
            <div>Loading...</div>
          </div>
        </div>
        <div class="container">
          <div class="mx-auto text-sm font-medium text-gray-700 border-t">
            <div class="flex">
              <button class="block mr-2" disabled>
                <FeatherIcon
                  name="circle"
                  class="w-4 text-gray-300 animate-pulse"
                />
              </button>
              <div class="w-[70%] py-2">
                <div class="w-40 py-2 bg-gray-100 rounded animate-pulse"></div>
              </div>
              <div class="w-[15%]"></div>
              <div class="w-[10%]"></div>
            </div>
          </div>
        </div>
      </template>
      <template v-if="$resources.tasks.data">
        <div v-for="section in project.doc.sections" :key="section.name">
          <div class="container py-2 mx-auto" v-if="!section.noSection">
            <div class="flex items-center -ml-8">
              <Button
                class="mr-1"
                appearance="minimal"
                @click="section.open = !section.open"
                :icon="section.open ? 'chevron-down' : 'chevron-right'"
              />
              <div class="text-lg font-semibold text-gray-900">
                {{ section.title }}
                <span class="font-normal">
                  ({{ $resources.tasks.data[section.name]?.length }})
                </span>
              </div>
              <Dropdown
                placement="left"
                class="ml-1"
                :button="{
                  icon: 'more-horizontal',
                  appearance: 'minimal',
                }"
                :options="[
                  {
                    label: 'Delete',
                    icon: 'trash-2',
                    handler: () => {
                      deleteSectionDialog.show = true
                      deleteSectionDialog.section = section
                    },
                  },
                ]"
              />
            </div>
          </div>
          <div v-if="section.open">
            <Draggable
              v-model="$resources.tasks.data[section.name]"
              group="tasks"
              item-key="name"
              animation="150"
              @sort="updateTasks(section, $resources.tasks.data[section.name])"
            >
              <template #item="{ element: task }">
                <div
                  class="container"
                  v-show="!task.deleted && !task.deletionError"
                >
                  <div
                    class="mx-auto border-t hover:bg-gray-50 group"
                    @click.capture="task.isActive = true"
                    v-onOutsideClick="
                      () => {
                        task.isActive = false
                      }
                    "
                  >
                    <div class="flex -ml-6">
                      <div class="flex items-center w-[70%]">
                        <button
                          class="mr-2 group-hover:opacity-100"
                          :class="task.isActive ? 'opacity-100' : 'opacity-0'"
                        >
                          <DragHandleIcon class="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                          v-if="!task.loading"
                          class="block mr-2"
                          @click="
                            () => {
                              task.is_completed = !task.is_completed
                              $resources.tasks.setValue.submit({
                                name: task.name,
                                is_completed: task.is_completed,
                              })
                            }
                          "
                          :disabled="
                            $resources.tasks.setValue.loading &&
                            $resources.tasks.setValue.params.name === task.name
                          "
                          :aria-label="
                            task.is_completed
                              ? 'Mark as incomplete'
                              : 'Mark as complete'
                          "
                        >
                          <FeatherIcon
                            :name="task.is_completed ? 'check' : 'circle'"
                            class="w-4 transition-colors"
                            :class="{
                              'text-gray-500 hover:text-gray-700':
                                task.is_completed,
                              'text-gray-400 hover:text-gray-600':
                                !task.is_completed,
                            }"
                          />
                        </button>
                        <div class="w-4 h-4 pl-px mr-2" v-else>
                          <LoadingIndicator class="text-gray-500" />
                        </div>
                        <router-link
                          :to="{
                            name: 'ProjectTaskDetail',
                            params: { taskId: task.name },
                          }"
                          class="text-base w-full py-1.5 px-1 cursor-pointer"
                          :class="{
                            'line-through text-gray-600': task.is_completed,
                          }"
                        >
                          {{ task.title }}
                        </router-link>
                      </div>
                      <div class="w-[15%] flex flex-shrink-0">
                        <AssignUser
                          class="w-full h-full text-sm text-gray-700"
                          :class="
                            task.assignedUser || task.isActive
                              ? ''
                              : 'opacity-0 group-hover:opacity-100'
                          "
                          :users="users"
                          :assignedUser="task.assignedUser"
                          @update:assigned-user="
                            updateAssignedUser(task, $event)
                          "
                        />
                      </div>
                      <div class="w-[10%] flex-shrink-0">
                        <input
                          type="date"
                          class="w-full h-full p-0 text-sm bg-transparent border-none focus:outline-none"
                          :class="
                            task.due_date || task.isActive
                              ? 'text-gray-700'
                              : 'text-gray-500 opacity-0 group-hover:opacity-100'
                          "
                          :value="(task.due_date || '').split(' ')[0]"
                          @change="
                            (e) => {
                              task.due_date = e.target.value
                              $resources.tasks.setValue.submit({
                                name: task.name,
                                due_date: task.due_date,
                              })
                            }
                          "
                        />
                      </div>
                      <div
                        class="w-[5%] flex items-center justify-end flex-shrink-0 group-hover:opacity-100"
                        :class="task.isActive ? 'opacity-100' : 'opacity-0'"
                      >
                        <Dropdown
                          :button="{
                            icon: 'more-horizontal',
                            appearance: 'minimal',
                          }"
                          :options="[
                            {
                              label: 'Delete',
                              icon: 'trash-2',
                              handler: () => {
                                deleteTask(task)
                              },
                            },
                          ]"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </Draggable>
            <div class="container mb-4">
              <div class="mx-auto text-sm font-medium text-gray-700 border-t">
                <div class="flex">
                  <button class="block mr-2">
                    <FeatherIcon
                      name="circle"
                      class="w-4 text-gray-400 transition-colors hover:text-gray-600"
                    />
                  </button>
                  <div class="w-[70%]">
                    <input
                      :ref="(ref) => setNewTaskRef(ref, section.name)"
                      class="w-full p-1 text-base font-medium text-gray-700 border-none focus:ring-0"
                      type="text"
                      @keydown.enter="
                        createTask({
                          title: newTaskRefs[section.name].value,
                          project: project.doc.name,
                          project_section: section.name,
                        })
                      "
                      placeholder="Add a task"
                      :disabled="$resources.tasks.insert.loading"
                    />
                  </div>
                  <div class="w-[15%]"></div>
                  <div class="w-[15%]"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div class="container pb-40 mx-auto mt-4">
        <div class="-ml-8">
          <Button
            v-show="!addingNewSection"
            icon-left="plus"
            appearance="white"
            @click="
              () => {
                addingNewSection = true
                $nextTick(() => {
                  $refs.newSectionInput.focus()
                })
              }
            "
          >
            Add section
          </Button>
          <div class="flex items-center" v-if="addingNewSection">
            <Button
              :icon="project.createSection.loading ? 'loader' : 'chevron-right'"
              class="mr-1"
            />
            <input
              ref="newSectionInput"
              type="text"
              class="p-0 text-lg font-semibold text-gray-900 border-none focus:ring-0"
              v-model="newSectionTitle"
              @keydown.enter="createSection(newSectionTitle)"
              @keydown.esc="cancelAddingNewSection"
              @blur="cancelAddingNewSection"
              :disabled="project.createSection.loading"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- task detail -->
    <router-view v-slot="{ Component }">
      <transition
        enter-from-class="translate-x-full"
        enter-to-class="translate-x-0"
        enter-active-class="transition duration-300 ease-out"
        leave-from-class="translate-x-0"
        leave-to-class="translate-x-full"
        leave-active-class="transition duration-150 ease-in"
      >
        <div
          v-if="$route.name == 'ProjectTaskDetail'"
          class="absolute top-0 bottom-0 right-0 w-1/2 bg-white border-l"
        >
          <component
            class="h-full"
            :is="Component"
            :project="project"
            @task-update="$resources.tasks.reload()"
          />
        </div>
      </transition>
    </router-view>

    <Dialog
      :options="{
        title: 'Delete Section',
        icon: {
          name: 'trash-2',
          appearance: 'danger',
        },
        message: `Are you sure you want to delete the section: ${deleteSectionDialog.section?.title}?`,
        actions: [
          {
            label: 'Delete',
            appearance: 'danger',
            loading: project.deleteSection.loading,
            handler: () => {
              project.deleteSection.submit(
                { section: deleteSectionDialog.section.name },
                {
                  onSuccess() {
                    deleteSectionDialog.section = null
                    deleteSectionDialog.show = false
                  },
                }
              )
            },
          },
          {
            label: 'Cancel',
          },
        ],
      }"
      v-model="deleteSectionDialog.show"
      @update:modelValue="
        (val) => {
          if (!val) {
            deleteSectionDialog.section = null
            project.deleteSection.reset()
          }
        }
      "
    >
      <template #body-content>
        <p class="text-sm text-gray-600">
          Are you sure you want to delete the section:
          <strong>{{ deleteSectionDialog.section?.title }}</strong>
          ?
        </p>
        <ErrorMessage
          class="mt-2"
          :message="project.deleteSection.error?.messages"
        />
      </template>
    </Dialog>
  </div>
</template>
<script>
import {
  Dropdown,
  Spinner,
  onOutsideClickDirective,
  LoadingIndicator,
} from 'frappe-ui'
import Draggable from 'vuedraggable'
import AssignUser from '@/components/AssignUser.vue'
import DragHandleIcon from '@/components/DragHandleIcon.vue'

export default {
  name: 'ProjectDetailTasks',
  props: ['project'],
  components: {
    Dropdown,
    Spinner,
    AssignUser,
    Draggable,
    DragHandleIcon,
    LoadingIndicator,
  },
  directives: {
    onOutsideClick: onOutsideClickDirective,
  },
  data() {
    return {
      activeTask: null,
      addingNewSection: false,
      deleteSectionDialog: { section: null, show: false },
      newSectionTitle: '',
    }
  },
  resources: {
    tasks() {
      return {
        type: 'list',
        cache: ['Project Tasks', this.project.doc.name],
        doctype: 'Team Task',
        fields: ['*'],
        filters: {
          project: this.project.doc.name,
        },
        order_by: 'idx asc, creation asc',
        transform(data) {
          return this.transformTasksIntoSections(data)
        },
        setValue: {
          onSuccess() {
            this.project.reload()
          },
        },
      }
    },
    assignTask() {
      return {
        method: 'teams.api.assign_task',
        onSuccess() {
          this.$resources.tasks.reload()
        },
      }
    },
  },
  computed: {
    users() {
      return this.project.doc?.members || []
    },
  },
  methods: {
    createTask(values) {
      this.$resources.tasks.setData((data) => {
        let section = data[values.project_section]
        values.name = `temp-task-${Math.random()}`
        values.loading = true // loading state while inserting
        section.push(values)
        return data
      })

      this.$nextTick(() => {
        this.$resources.tasks.insert.submit(values)

        let input = this.newTaskRefs[values.project_section]
        if (input) {
          input.value = ''
          setTimeout(() => {
            input.focus()
          }, 300)
        }
      })
    },
    deleteTask(task) {
      task.deleted = true
      this.$resources.tasks.delete.submit(task.name, {
        onError(e) {
          task.deleted = false
          this.$toast({
            icon: 'alert-triangle',
            iconClasses: 'text-red-600',
            title: 'Error deleting task',
            text: e.messages.join('\n'),
            timeout: 10,
          })
        },
      })
    },
    updateTasks(section, tasks) {
      // local update
      tasks.forEach((task, i) => {
        task.idx = i + 1
        task.project_section = section.name
      })

      // server update
      this.project.updateTasksOrder.submit({
        tasks: tasks.map((task) => ({
          name: task.name,
          project_section: task.project_section,
          idx: task.idx,
        })),
      })
    },
    createSection(title) {
      this.project.createSection.submit(
        { title },
        {
          onSuccess: () => {
            this.addingNewSection = false
            this.newSectionTitle = ''
            this.$resources.tasks.reload()
          },
        }
      )
    },
    cancelAddingNewSection() {
      this.addingNewSection = false
      this.newSectionTitle = ''
    },
    transformTasksIntoSections(data) {
      let tasks = data || []
      let noSection = '__noSection'
      let bySection = {
        __noSection: [],
      }
      for (let section of this.project.doc.sections) {
        bySection[section.name] = []
      }
      tasks.forEach((task) => {
        let section = task.project_section || noSection
        bySection[section].push(task)
      })

      for (let section in bySection) {
        let tasks = bySection[section]
        tasks.sort((a, b) => a.idx - b.idx)
      }
      return bySection
    },
    setNewTaskRef(ref, status) {
      this.newTaskRefs = this.newTaskRefs || {}
      this.newTaskRefs[status] = ref
    },
    updateAssignedUser(task, user) {
      task.assignedUser = user
      this.$resources.assignTask.submit({
        task: task.name,
        user: user.email,
      })
    },
  },
}
</script>
