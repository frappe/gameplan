<template>
  <div class="border-b">
    <nav class="-mb-px flex space-x-8" aria-label="Tabs">
      <Links
        :links="links"
        class="whitespace-nowrap border-b-2 py-3 text-base font-medium leading-none"
        v-slot="{ link }"
      >
        <div class="items- flex items-end space-x-1">
          <FeatherIcon :name="link.icon" v-if="link.icon" class="h-3.5 w-3.5" />
          <span>
            {{ link.name }}
          </span>
        </div>
      </Links>
    </nav>
  </div>
</template>
<script>
import Links from './Links.vue'
export default {
  name: 'Tabs',
  props: ['tabs'],
  components: { Links },
  computed: {
    links() {
      return this.tabs.map((tab) => {
        return {
          ...tab,
          class: tab.isActive
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
        }
      })
    },
  },
}
</script>
