<template>
  <div class="border-b">
    <div class="sm:hidden">
      <label :for="domId" class="sr-only">Select a tab</label>
      <select
        :id="domId"
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
            class="py-3 text-base font-medium leading-none border-b-2 whitespace-nowrap"
            v-slot="{ link }"
          >
            <div class="flex items-end space-x-1 items-">
              <FeatherIcon
                :name="link.icon"
                v-if="link.icon"
                class="w-3.5 h-3.5"
              />
              <span>
                {{ link.name }}
              </span>
            </div>
          </Links>
        </nav>
      </div>
    </div>
  </div>
</template>
<script>
import Links from './Links.vue'
export default {
  name: 'Tabs',
  props: ['tabs'],
  computed: {
    domId() {
      return 'id-' + Math.random().toString(36).substring(2, 15)
    },
  },
  components: { Links },
}
</script>
