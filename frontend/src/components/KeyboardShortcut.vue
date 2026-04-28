<template>
  <div
    class="inline-flex items-center gap-0.5 text-sm"
    :class="{ 'bg-surface-gray-2 rounded-sm text-ink-gray-5 p-0.5': bg, 'text-ink-gray-4': !bg }"
  >
    <span v-if="ctrl"><span class="lucide-command w-3 h-3" /></span>
    <span v-if="shift"><span class="lucide-shift w-3 h-3" /></span>
    <span v-if="alt"><span class="lucide-alt w-3 h-3" /></span>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
defineProps({
  ctrl: Boolean,
  shift: Boolean,
  alt: Boolean,
  shortcut: String,
  bg: Boolean,
})
</script>
