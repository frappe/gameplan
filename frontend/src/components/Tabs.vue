<template>
  <div class="border-b">
    <nav class="flex -mb-px space-x-8" aria-label="Tabs">
      <Links
        :links="tabs"
        class="py-3 text-base font-medium leading-none border-b-2 whitespace-nowrap"
        v-slot="{ link }"
      >
        <div class="flex items-end space-x-1 items-">
          <FeatherIcon :name="link.icon" v-if="link.icon" class="w-3.5 h-3.5" />
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
}
</script>
