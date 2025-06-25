<template>
  <AppLink
    :to="to"
    :isActive="isActive"
    class="flex items-center rounded px-2 py-1 text-ink-gray-7 transition h-7"
    activeClass="bg-surface-selected shadow-sm"
    inactiveClass="hover:bg-surface-gray-2"
  >
    <div class="flex w-full items-center space-x-2">
      <span class="grid h-5 w-6 place-items-center">
        <slot name="prefix" />
      </span>
      <span class="text-sm"><slot /></span>
      <div v-if="$slots.suffix" class="!ml-auto">
        <slot name="suffix" />
      </div>
    </div>
  </AppLink>
</template>
<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

defineProps<{
  to: RouteLocationRaw
  isActive?: boolean
}>()
</script>
