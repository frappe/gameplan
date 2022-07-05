<template>
  <div class="flex">
    <div
      class="flex-shrink-0 overflow-auto"
      :class="isTaskOpen ? 'w-1/2' : 'w-full'"
    >
      <div>
        <div class="px-6">
          <div class="flex items-center h-10 text-base text-gray-600 border-b">
            <div :class="isTaskOpen ? 'w-full' : 'w-[70%]'">Task</div>
            <div class="w-[15%]" :class="isTaskOpen && 'hidden'">Assignee</div>
            <div class="w-[10%]" :class="isTaskOpen && 'hidden'">Due Date</div>
            <div class="w-[5%]" :class="isTaskOpen && 'hidden'"></div>
          </div>
        </div>
        <template v-if="!$resources.tasks.data">
          <div class="px-6 py-2 text-lg font-semibold text-gray-900">
            <div class="flex items-center">
              <Button
                class="mr-1"
                appearance="minimal"
                :icon="'chevron-down'"
                :disabled="true"
              />
              <div>Loading...</div>
            </div>
          </div>
          <div class="px-6">
            <div class="text-sm font-medium text-gray-700 border-t">
              <div class="flex pl-8">
                <div class="grid place-items-center ml-0.5 mr-1">
                  <Input type="checkbox" :disabled="true" />
                </div>
                <div class="py-2" :class="isTaskOpen ? 'w-full' : 'w-[70%]'">
                  <div
                    class="w-40 py-2 bg-gray-100 rounded animate-pulse"
                  ></div>
                </div>
                <div class="w-[15%]" :class="isTaskOpen && 'hidden'"></div>
                <div class="w-[10%]" :class="isTaskOpen && 'hidden'"></div>
              </div>
            </div>
          </div>
        </template>

        <template v-if="$resources.tasks.data">
          <Draggable
            v-model="project.doc.sections"
            group="sections"
            item-key="name"
            animation="150"
            ghostClass="opacity-50"
            handle=".drag-handle-section"
            @choose="sectionIsDragging = true"
            @unchoose="sectionIsDragging = false"
            @sort="updateSections"
          >
            <template #item="{ element: section }">
              <div class="pb-2 pl-1 pr-6">
                <div class="py-2" v-if="!section.noSection">
                  <div class="flex items-center group">
                    <button
                      class="grid flex-shrink-0 w-4 h-4 mr-1 border border-transparent opacity-0 drag-handle-section place-items-center group-hover:opacity-100"
                    >
                      <DragHandleIcon class="w-4 h-4 text-gray-400" />
                    </button>
                    <Button
                      class="mr-1"
                      appearance="minimal"
                      @click="section.open = !section.open"
                      :icon="section.open ? 'chevron-down' : 'chevron-right'"
                    />
                    <Popover>
                      <template #target="{ open: openEditPopup }">
                        <div class="flex items-center">
                          <div class="text-lg font-semibold text-gray-900">
                            {{ section.title }}
                            <span class="font-normal">
                              ({{
                                $resources.tasks.data[section.name]?.length
                              }})
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
                                label: 'Edit title',
                                icon: 'edit',
                                handler: () => {
                                  openEditPopup()
                                  editSectionTitlePopup.section = section
                                },
                              },
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
                      </template>
                      <template #body-main="{ close }">
                        <div class="p-2">
                          <div class="flex items-end space-x-1">
                            <Input
                              label="Edit title and hit enter"
                              type="text"
                              placeholder="Section title"
                              :value="section.title"
                              @keydown.enter="
                                (e) => {
                                  if (e.target.value) {
                                    section.title = e.target.value
                                    updateSections()
                                  }
                                  close()
                                  editSectionTitlePopup = {
                                    show: false,
                                    section: null,
                                  }
                                }
                              "
                            />
                            <Button
                              @click="
                                () => {
                                  close()
                                  editSectionTitlePopup = {
                                    show: false,
                                    section: null,
                                  }
                                }
                              "
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      </template>
                    </Popover>
                  </div>
                </div>
                <div class="pl-5" v-show="section.open">
                  <Draggable
                    :class="
                      taskIsDragging &&
                      !$resources.tasks.data[section.name].length
                        ? 'min-h-[1px] pt-1 -mt-1'
                        : ''
                    "
                    v-model="$resources.tasks.data[section.name]"
                    group="tasks"
                    item-key="name"
                    animation="150"
                    ghostClass="bg-gray-100"
                    handle=".drag-handle-task"
                    @choose="taskIsDragging = true"
                    @unchoose="taskIsDragging = false"
                    @sort="
                      updateTasks(section, $resources.tasks.data[section.name])
                    "
                  >
                    <template #item="{ element: task }">
                      <div
                        v-show="!task.deleted && !task.deletionError"
                        class="rounded-lg group"
                        :class="[
                          openTask === task.name
                            ? 'bg-gray-100'
                            : !taskIsDragging
                            ? 'hover:bg-gray-50'
                            : '',
                        ]"
                        @click.capture="task.isActive = true"
                        v-onOutsideClick="
                          () => {
                            task.isActive = false
                          }
                        "
                      >
                        <div class="flex">
                          <div
                            class="flex items-center"
                            :class="isTaskOpen ? 'w-full' : 'w-[70%]'"
                          >
                            <button
                              class="drag-handle-task flex-shrink-0 grid mr-1 w-[30px] h-[30px] border border-transparent place-items-center group-hover:opacity-100"
                              :class="
                                task.isActive ? 'opacity-100' : 'opacity-0'
                              "
                            >
                              <DragHandleIcon class="w-4 h-4 text-gray-400" />
                            </button>
                            <div class="mr-1" v-if="!task.loading">
                              <Input
                                type="checkbox"
                                :aria-label="
                                  task.is_completed
                                    ? 'Mark as incomplete'
                                    : 'Mark as complete'
                                "
                                v-model="task.is_completed"
                                @change="
                                  (val) => {
                                    task.is_completed = val
                                    $resources.tasks.setValue.submit({
                                      name: task.name,
                                      is_completed: task.is_completed,
                                    })
                                  }
                                "
                                :disabled="
                                  $resources.tasks.setValue.loading &&
                                  $resources.tasks.setValue.params.name ===
                                    task.name
                                "
                              />
                            </div>
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
                          <div
                            class="w-[15%] flex flex-shrink-0"
                            :class="isTaskOpen && 'hidden'"
                          >
                            <div class="flex items-center space-x-1">
                              <Avatar
                                size="sm"
                                :imageURL="$user(task.assigned_to).user_image"
                                :label="$user(task.assigned_to).full_name"
                              />
                              <span class="text-base text-gray-900">
                                {{ $user(task.assigned_to).full_name }}
                              </span>
                            </div>
                          </div>
                          <div
                            class="w-[10%] flex-shrink-0"
                            :class="isTaskOpen && 'hidden'"
                          >
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
                            :class="[
                              task.isActive ? 'opacity-100' : 'opacity-0',
                              isTaskOpen && 'hidden',
                            ]"
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
                    </template>
                  </Draggable>
                  <div class="mb-2">
                    <div
                      class="text-sm font-medium text-gray-700 rounded-lg focus-within:bg-gray-50"
                    >
                      <div class="flex pl-8">
                        <div class="grid place-items-center ml-0.5 mr-1">
                          <Input type="checkbox" :disabled="true" />
                        </div>
                        <div :class="isTaskOpen ? 'w-full' : 'w-[70%]'">
                          <input
                            :ref="(ref) => setNewTaskRef(ref, section.name)"
                            class="w-full p-1 text-base font-medium text-gray-700 bg-transparent border-none focus:ring-0"
                            type="text"
                            @keydown.enter="
                              createTask({
                                title: newTaskRefs[section.name].value,
                                project: project.doc.name,
                                project_section: section.name,
                              })
                            "
                            placeholder="Add a task..."
                            :disabled="$resources.tasks.insert.loading"
                          />
                        </div>
                        <div
                          class="w-[15%]"
                          :class="isTaskOpen && 'hidden'"
                        ></div>
                        <div
                          class="w-[15%]"
                          :class="isTaskOpen && 'hidden'"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </Draggable>
        </template>
        <div class="px-6 pb-40 mt-4">
          <div>
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
                :icon="
                  project.createSection.loading ? 'loader' : 'chevron-right'
                "
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

    <!-- task detail -->
    <router-view v-slot="{ Component }">
      <div
        v-if="$route.name == 'ProjectTaskDetail'"
        class="w-1/2 bg-white border-l"
      >
        <component
          class="h-full"
          :is="Component"
          :project="project"
          @task-update="$resources.tasks.reload()"
        />
      </div>
    </router-view>
  </div>
</template>
<script>
import {
  Avatar,
  Dropdown,
  Spinner,
  onOutsideClickDirective,
  LoadingIndicator,
  Popover,
} from 'frappe-ui'
import Draggable from 'vuedraggable'
import DragHandleIcon from '@/components/DragHandleIcon.vue'

export default {
  name: 'ProjectDetailTasks',
  props: ['project'],
  components: {
    Dropdown,
    Spinner,
    Draggable,
    DragHandleIcon,
    LoadingIndicator,
    Popover,
    Avatar,
  },
  directives: {
    onOutsideClick: onOutsideClickDirective,
  },
  data() {
    return {
      addingNewSection: false,
      deleteSectionDialog: { section: null, show: false },
      newSectionTitle: '',
      taskIsDragging: false,
      editSectionTitlePopup: { show: false, section: null },
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
    isTaskOpen() {
      return this.$route.name == 'ProjectTaskDetail'
    },
    openTask() {
      return this.$route.params.taskId
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
    updateSections() {
      // local update
      this.project.doc.sections.forEach((section, i) => {
        section.idx = i + 1
      })

      // server update
      this.project.setValue.submit({
        sections: this.project.doc.sections.map((section) => ({
          name: section.name,
          idx: section.idx,
          title: section.title,
          type: section.type,
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
