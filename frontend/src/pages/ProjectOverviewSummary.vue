<template>
  <div v-if="cards.length" class="grid grid-cols-2 gap-5 sm:grid-cols-4">
    <router-link
      class="block rounded-xl bg-gray-100 px-3.5 py-2.5"
      v-for="card in cards"
      :key="card.subtitle"
      :to="card.route"
    >
      <div
        :class="[
          'text-xl font-bold',
          card.count > 0 ? card.titleStyle : 'text-gray-700',
        ]"
      >
        {{ card.count }}
      </div>
      <div class="text-base text-gray-700">{{ card.subtitle }}</div>
    </router-link>
  </div>
</template>
<script>
export default {
  name: 'ProjectOverviewSummary',
  props: ['project'],
  computed: {
    cards() {
      if (this.project.doc.summary.total_tasks === 0) {
        return []
      }

      let route = {
        name: 'ProjectTasks',
        params: {
          teamId: this.project.doc.team,
          projectId: this.project.doc.name,
        },
      }

      return [
        {
          count: this.project.doc.summary.completed_tasks,
          titleStyle: 'text-green-600',
          subtitle: 'Completed Tasks',
          route: {
            ...route,
            query: { open: false },
          },
        },
        {
          count: this.project.doc.summary.pending_tasks,
          titleStyle: 'text-yellow-600',
          subtitle: 'Pending Tasks',
          route: {
            ...route,
            query: { open: true },
          },
        },
        {
          count: this.project.doc.summary.overdue_tasks,
          titleStyle: 'text-red-700',
          subtitle: 'Overdue Tasks',
          route: {
            ...route,
            query: { open: true },
          },
        },
        {
          count: this.project.doc.summary.total_tasks,
          titleStyle: 'text-gray-700',
          subtitle: 'Total Tasks',
          route: {
            ...route,
            query: { open: true },
          },
        },
      ]
    },
  },
}
</script>
