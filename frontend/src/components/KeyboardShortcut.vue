<template>
  <div class="inline-flex items-center gap-0.5 text-sm text-ink-gray-4">
    <span v-if="ctrl"><LucideCommand class="w-3 h-3" /></span>
    <span v-if="shift"><LucideShift class="w-3 h-3" /></span>
    <span v-if="alt"><LucideAlt class="w-3 h-3" /></span>
    <slot></slot>
  </div>
</template>
<script setup lang="ts">
import LucideCommand from '~icons/lucide/command'
import LucideShift from '~icons/lucide/arrow-big-up'
import LucideAlt from '~icons/lucide/option'

defineProps({
  ctrl: Boolean,
  shift: Boolean,
  alt: Boolean,
  shortcut: String,
})
</script>
