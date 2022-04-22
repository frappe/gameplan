<template>
  <div class="mt-4 space-y-4" v-if="$resources.allTasks.data">
    <section v-for="(tasks, project) in groupedTasks" :key="project">
      <h3 class="py-2 text-lg font-medium">
        <span v-if="tasks.length && tasks[0].team_title">
          {{ tasks[0].team_title }}
          /
        </span>
        <span>
          {{ project }}
        </span>
      </h3>
      <div class="border-t border-gray-100 divide-y divide-gray-100">
        <div
          v-if="
            project == 'Personal Tasks' && date >= $dayjs().format('YYYY-MM-DD')
          "
          class="flex items-center px-3 py-3 focus-within:bg-gray-100"
        >
          <TaskCheck :checked="false" />
          <input
            class="w-full text-base font-medium text-gray-900 bg-transparent focus:outline-none"
            placeholder="Add task"
            v-model="newTask"
            @keydown.enter="$resources.newTask.submit(this.newTask)"
            :disabled="$resources.newTask.loading"
          />
        </div>
        <div
          class="py-3 text-base text-gray-500"
          v-if="!tasks.length && date < $dayjs().format('YYYY-MM-DD')"
        >
          No Tasks
        </div>
        <router-link
          :key="task.name"
          v-for="task in tasks"
          class="flex items-center px-3 py-3 hover:bg-gray-50"
          :to="`/task/${task.name}`"
        >
          <TaskCheck
            @click.stop.prevent
            :checked="task.is_completed || 0"
            @change="
              (completed) =>
                $resources.markAsComplete.submit({ task, completed })
            "
          />
          <div
            class="text-base font-medium"
            :class="
              task.is_completed ? 'line-through text-gray-500' : 'text-gray-900'
            "
          >
            {{ task.title }}
          </div>
          <Badge class="ml-auto" v-if="task.due_date < date"> Overdue </Badge>
        </router-link>
      </div>
    </section>
  </div>
</template>
<script>
import TaskCheck from '@/components/TaskCheck.vue'

export default {
  name: 'DailyPlannerTasks',
  props: ['date'],
  components: { TaskCheck },
  data() {
    return {
      newTask: '',
    }
  },
  resources: {
    allTasks() {
      return {
        method: 'teams.api.tasks_for_day',
        params: {
          date: this.date,
        },
        auto: true,
      }
    },
    newTask() {
      return {
        method: 'frappe.client.insert',
        makeParams(title) {
          return {
            doc: {
              doctype: 'Team Task',
              due_date: this.date,
              title,
            },
          }
        },
        onSuccess() {
          this.newTask = ''
          this.$resources.allTasks.fetch()
        },
      }
    },
    markAsComplete() {
      return {
        method: 'frappe.client.set_value',
        makeParams({ task, completed }) {
          task.is_completed = completed
          return {
            doctype: 'Team Task',
            name: task.name,
            fieldname: {
              is_completed: completed,
            },
          }
        },
        onSuccess() {
          this.$resources.allTasks.fetch()
        },
      }
    },
  },
  computed: {
    groupedTasks() {
      let tasksByProject = {}
      let personalTasks = []
      this.$resources.allTasks.data.forEach((task) => {
        if (task.project_title) {
          if (!tasksByProject[task.project_title]) {
            tasksByProject[task.project_title] = []
          }
          tasksByProject[task.project_title].push(task)
        } else {
          personalTasks.push(task)
        }
      })

      for (let project in tasksByProject) {
        tasksByProject[project].sort((a, b) => {
          return a.idx - b.idx
        })
      }

      return {
        'Personal Tasks': personalTasks,
        ...tasksByProject,
      }
    },
  },
}
</script>
