<template>
  <Teleport v-if="target" :to="target">
    <div class="flex items-center gap-2">
      <slot />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, shallowRef } from 'vue'

const props = withDefaults(
  defineProps<{
    // 'mobile' is the phone header's right side; the other two sit in the desktop header.
    placement?: 'title' | 'actions' | 'mobile'
  }>(),
  {
    placement: 'actions',
  },
)

const targetSelector = computed(() => {
  const selectors = {
    title: '[data-space-header-title-actions]',
    actions: '[data-space-header-actions]',
    mobile: '[data-space-header-mobile-actions]',
  }
  return selectors[props.placement]
})

// Space.vue hides the header on a page route and brings it back in the same render as
// this tab. A Teleport that mounts before its target exists leaves a broken vnode, and
// unmounting it later throws and stops the route change. Teleport only once it is there.
const target = shallowRef<Element | null>(null)

onMounted(async () => {
  await nextTick()
  target.value = document.querySelector(targetSelector.value)
})
</script>
