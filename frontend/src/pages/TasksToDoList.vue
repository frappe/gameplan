<template>
  <div class="px-3.5 py-5">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-gray-900">My Tasks</h1>
      <Button
        iconLeft="plus"
        @click="
          () => {
            addingTask.show = !addingTask.show
            $nextTick(() => {
              $refs.newTaskInput.focus()
            })
          }
        "
      >
        Add a task
      </Button>
    </header>
    <div class="mt-3">
      <div v-show="addingTask.show">
        <div class="border rounded-lg">
          <div class="flex items-center p-2 space-x-3 text-base leading-none">
            <Input type="checkbox" />
            <input
              ref="newTaskInput"
              type="text"
              placeholder="Add a task..."
              class="w-full p-0 text-base leading-none text-gray-900 border-none focus:ring-0"
              v-model="addingTask.title"
            />
          </div>
          <div class="flex items-stretch pb-2 pl-8 space-x-2">
            <button
              class="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200"
              :class="{
                '!bg-gray-300':
                  addingTask.due_date === $dayjs().format('YYYY-MM-DD'),
              }"
              @click="addingTask.due_date = $dayjs().format('YYYY-MM-DD')"
            >
              Today
            </button>
            <button
              class="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200"
              :class="{
                '!bg-gray-300':
                  addingTask.due_date ===
                  $dayjs().add(1, 'day').format('YYYY-MM-DD'),
              }"
              @click="
                addingTask.due_date = $dayjs()
                  .add(1, 'day')
                  .format('YYYY-MM-DD')
              "
            >
              Tomorrow
            </button>
            <DatePicker
              v-model="addingTask.due_date"
              :format-value="(val) => $dayjs(val).format('ddd MMM DD, YYYY')"
              input-class="text-xs"
              placeholder="Set due date"
            />
          </div>
        </div>
        <div class="mt-2 space-x-2 text-right">
          <Button @click="resetAddingTask"> Cancel </Button>
          <Button
            appearance="primary"
            @click="
              () => {
                $resources.tasks.insert.submit({
                  title: addingTask.title,
                  due_date: addingTask.due_date,
                })
                resetAddingTask()
              }
            "
            :loading="$resources.tasks.insert.loading"
          >
            Save
          </Button>
        </div>
      </div>
    </div>
    <div class="mt-3" v-for="section in sections" :key="section.title">
      <div :set="(tasks = getTasks(section))"></div>
      <div class="flex items-center">
        <Button
          :icon="section.open ? 'chevron-down' : 'chevron-right'"
          appearance="minimal"
          @click="section.open = !section.open"
        />
        <span class="ml-1 text-base font-semibold">
          {{ section.title }} ({{ tasks.length }})
        </span>
      </div>
      <div class="space-y-1.5 mt-1.5" v-show="section.open">
        <div
          class="p-2 border rounded-lg"
          v-for="task in tasks"
          :key="task.name"
        >
          <div class="flex items-center space-x-3">
            <Input
              type="checkbox"
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
                $resources.tasks.setValue.params.name === task.name
              "
            />
            <span
              class="text-base leading-none"
              :class="{
                'line-through text-gray-600': task.is_completed,
              }"
            >
              {{ task.title }}
            </span>
          </div>
          <div
            class="mt-1 text-xs text-gray-700 pl-7"
            v-if="section.title != 'Today' && task.due_date"
          >
            {{ $dayjs(task.due_date).format('ddd, MMM DD') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { DatePicker } from 'frappe-ui'

export default {
  name: 'TasksToDoList',
  components: {
    DatePicker,
  },
  data() {
    return {
      addingTask: { show: false, title: null, due_date: null },
      sections: [
        {
          title: 'Today',
          open: true,
        },
        {
          title: 'This week',
          open: false,
        },
        {
          title: 'Unscheduled',
          open: false,
        },
      ],
    }
  },
  resources: {
    tasks() {
      return {
        type: 'list',
        doctype: 'Team Task',
        cache: 'Tasks',
        fields: ['name', 'title', 'due_date', 'is_completed', 'idx'],
        filters: {
          project: ['is', 'not set'],
        },
        order_by: 'idx desc',
      }
    },
  },
  methods: {
    getTasks(section) {
      return (this.$resources.tasks.data || []).filter((task) => {
        let due = this.$dayjs(task.due_date)
        if (section.title === 'Today') {
          return due.isSame(this.$dayjs(), 'day')
        } else if (section.title === 'This week') {
          return (
            due.isSame(this.$dayjs(), 'week') &&
            !due.isSame(this.$dayjs(), 'day')
          )
        } else if (section.title === 'Unscheduled') {
          return !task.due_date
        }
      })
    },
    createTask(title, due_date) {
      this.$resources.tasks.insert.submit({ title, due_date })
    },
    resetAddingTask() {
      this.addingTask = { show: false, title: null, due_date: null }
    },
  },
}
</script>
