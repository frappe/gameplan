<template>
  <div class="h-full" v-if="$resources.team.data">
    <div class="py-4 bg-white border-b">
      <div class="mx-auto container">
        <Breadcrumbs :pages="breadcrumbs" />

        <div class="mt-2" v-if="false">
          <div class="sm:hidden">
            <label for="tabs" class="sr-only">Select a tab</label>
            <!-- Use an "onChange" listener to redirect the user to the selected tab URL. -->
            <select
              id="tabs"
              name="tabs"
              class="block w-full py-2 pl-3 pr-10 text-base border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              @change="$router.push($event.target.value)"
            >
              <option
                v-for="tab in tabs"
                :key="tab.name"
                :selected="$route.fullPath === tab.route"
                :value="tab.route"
              >
                {{ tab.name }}
              </option>
            </select>
          </div>
          <div class="hidden sm:block">
            <div>
              <nav class="flex -mb-px space-x-8" aria-label="Tabs">
                <Links
                  :links="tabs"
                  class="px-1 py-2 text-sm font-medium border-b-2 whitespace-nowrap"
                />
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
    <router-view v-if="team" :team="$resources.team.data" />
  </div>
</template>
<script>
import Links from '@/components/Links.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
export default {
  name: 'TeamPage',
  props: ['id'],
  components: {
    Links,
    Breadcrumbs,
  },
  resources: {
    team() {
      return {
        method: 'teams.api.get_team',
        cache: ['team', this.id],
        params: {
          name: this.id,
        },
        auto: true,
      }
    },
  },
  computed: {
    team() {
      return this.$resources.team.data ? this.$resources.team.data : null
    },
    breadcrumbs() {
      let fullPath = this.$route.fullPath
      let pages = [
        { label: 'Teams', route: '/' },
        {
          label: this.team.title,
          route: `/${this.team.name}`,
          current: fullPath === `/${this.team.name}`,
        },
      ]
      console.log(this.$route)
      if (this.$route.params.projectId) {
        let projectId = this.$route.params.projectId
        let route = `/${this.team.name}/projects/${projectId}`
        pages.push({
          label: projectId,
          route,
          current: fullPath === route,
        })
      }
      return pages
    },
    tabs() {
      return [
        {
          name: 'Home',
          route: `/${this.id}`,
          class: this.tabLinkClasses,
        },
        {
          name: 'Projects',
          route: `/${this.id}/projects`,
          class: this.tabLinkClasses,
        },
        {
          name: 'Members',
          route: `/${this.id}/members`,
          class: this.tabLinkClasses,
        },
        {
          name: 'Discussions',
          route: `/${this.id}/discussions`,
          class: this.tabLinkClasses,
        },
        {
          name: 'Documents',
          route: `/${this.id}/documents`,
          class: this.tabLinkClasses,
        },
      ]
    },
  },
  methods: {
    tabLinkClasses($route, link) {
      let active = false
      if ($route.fullPath === link.route) {
        active = true
      }
      if (link.name != 'Home' && $route.fullPath.startsWith(link.route)) {
        active = true
      }
      if (active) {
        return 'border-blue-500 text-blue-600'
      }
      return 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
    },
  },
}
</script>
