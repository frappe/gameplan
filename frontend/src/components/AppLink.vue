<template>
  <a v-if="isExternalLink" v-bind="$attrs" :href="props.to" target="_blank">
    <slot />
  </a>
  <RouterLink
    v-else
    v-bind="$props"
    custom
    :to="props.to"
    v-slot="{ isActive: slotIsActive, href, navigate }"
  >
    <a
      v-bind="$attrs"
      class="focus:outline-none focus-visible:ring focus-visible:ring-gray-400"
      :href="href"
      @click="navigate"
      :class="computedIsActive(slotIsActive) ? activeClass : inactiveClass"
    >
      <slot />
    </a>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  // @ts-ignore
  ...RouterLink.props,
  inactiveClass: String,
  isActive: {
    type: Boolean,
    default: undefined,
  },
})

const computedIsActive = (slotIsActive: boolean) => {
  if (props.isActive !== undefined) {
    return props.isActive
  }
  return slotIsActive
}

const isExternalLink = computed(() => {
  return typeof props.to === 'string' && props.to.startsWith('http')
})
</script>
