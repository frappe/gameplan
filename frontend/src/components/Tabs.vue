<template>
  <div class="border-b">
    <nav class="-mb-px flex space-x-8" aria-label="Tabs">
      <Links :links="links" class="whitespace-nowrap border-b-2 py-1.5 text-base" v-slot="{ link }">
        <div class="items- flex items-end space-x-1">
          <component :is="link.icon" v-if="link.icon" class="h-3.5 w-3.5" />
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
            ? 'border-gray-900 text-ink-gray-8'
            : 'border-transparent text-ink-gray-5 hover:text-ink-gray-6 hover:border-outline-gray-2',
        }
      })
    },
  },
}
</script>
