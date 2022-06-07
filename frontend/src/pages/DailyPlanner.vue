<template>
  <header class="flex items-center px-4 py-3 border-b">
    <h1 class="text-lg font-semibold text-gray-900">Daily Planner</h1>
  </header>
  <div
    class="relative grid justify-between h-12 max-w-2xl grid-cols-7 px-4 mx-auto mt-4"
  >
    <router-link
      class="flex flex-col items-center justify-center h-full px-5 border-b-2"
      v-for="day in days"
      :key="day"
      :to="{
        name: 'DailyPlannerTasks',
        params: { date: day.format('YYYY-MM-DD') },
      }"
      :class="
        day.format('YYYY-MM-DD') == date
          ? 'border-blue-500 font-medium'
          : 'hover:bg-gray-50 border-gray-100 '
      "
    >
      <div class="text-xs text-gray-600">
        {{ day.format('ddd') }}
      </div>
      <div
        class="text-lg"
        :class="[
          day.isToday() ? 'text-blue-500 font-semibold' : 'text-gray-800',
          day.format('YYYY-MM-DD') == date ? 'font-semibold' : '',
        ]"
      >
        {{ day.format('D') }}
      </div>
    </router-link>
  </div>
  <main>
    <div class="max-w-2xl p-4 mx-auto">
      <h2 class="text-2xl font-bold">{{ $dayjs().format('dddd, MMM D') }}</h2>
      <Tabs class="mt-4" :tabs="tabs" />
      <router-view :date="date" />
    </div>
  </main>
</template>
<script>
import Links from '@/components/Links.vue'
import Tabs from '@/components/Tabs.vue'
export default {
  name: 'DailyPlanner',
  props: ['date'],
  components: {
    Links,
    Tabs,
  },
  computed: {
    tabs() {
      return [
        {
          name: 'Tasks',
          route: { name: 'DailyPlannerTasks', params: { date: this.date } },
          class: this.tabLinkClasses,
        },
        {
          name: 'Notes',
          route: { name: 'DailyPlannerNotes', params: { date: this.date } },
          class: this.tabLinkClasses,
        },
        {
          name: 'Calendar',
          route: { name: 'DailyPlannerCalendar', params: { date: this.date } },
          class: this.tabLinkClasses,
        },
      ]
    },
    days() {
      let today = this.$dayjs()
      let firstDay = today.startOf('week')
      let lastDay = today.endOf('week')
      let days = []
      let currentDay = firstDay
      while (currentDay <= lastDay) {
        days.push(currentDay)
        currentDay = currentDay.add(1, 'day')
      }
      return days
    },
  },
  mounted() {
    let fullPath = this.$route.fullPath
    if (fullPath.endsWith('/')) {
      fullPath = fullPath.slice(0, -1)
    }
    let today = this.$dayjs().format('YYYY-MM-DD')
    if (this.$route.name === 'DailyPlanner') {
      this.$router.push({ name: 'DailyPlannerTasks', params: { date: today } })
    }
  },
  methods: {
    tabLinkClasses($route, link) {
      // debugger
      let active = false
      if ($route.name === link.route?.name) {
        active = true
      } else if ($route.fullPath === link.route) {
        active = true
      }
      if (active) {
        return 'border-blue-500 text-blue-600'
      }
      return 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
    },
  },
  pageMeta() {
    return {
      title: 'Daily Planner',
      emoji: '📅',
    }
  },
}
</script>
