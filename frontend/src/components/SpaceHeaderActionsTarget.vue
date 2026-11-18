<template>
  <div
    class="flex items-center gap-2"
    :data-space-header-actions="placement === 'actions' ? '' : null"
    :data-space-header-title-actions="placement === 'title' ? '' : null"
    :data-space-header-mobile-actions="placement === 'mobile' ? '' : null"
    v-bind="$attrs"
  />
</template>

<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
})

withDefaults(
  defineProps<{
    placement?: 'title' | 'actions' | 'mobile'
  }>(),
  {
    placement: 'actions',
  },
)
</script>
