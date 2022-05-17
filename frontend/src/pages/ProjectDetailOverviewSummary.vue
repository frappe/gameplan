<template>
  <div v-if="cards.length" class="grid grid-cols-4 gap-5">
    <div
      class="bg-gray-100 rounded-xl px-3.5 py-2.5"
      v-for="card in cards"
      :key="card.subtitle"
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
    </div>
  </div>
</template>
<script>
export default {
  name: 'ProjectDetailOverviewSummary',
  props: ['project'],
  computed: {
    cards() {
      if (this.project.doc.summary.total_tasks === 0) {
        return []
      }

      return [
        {
          count: this.project.doc.summary.completed_tasks,
          titleStyle: 'text-green-600',
          subtitle: 'Completed Tasks',
        },
        {
          count: this.project.doc.summary.pending_tasks,
          titleStyle: 'text-yellow-600',
          subtitle: 'Pending Tasks',
        },
        {
          count: this.project.doc.summary.overdue_tasks,
          titleStyle: 'text-red-700',
          subtitle: 'Overdue Tasks',
        },
        {
          count: this.project.doc.summary.total_tasks,
          titleStyle: 'text-gray-700',
          subtitle: 'Total Tasks',
        },
      ]
    },
  },
}
</script>
