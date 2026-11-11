<template>
  <div
    class="flex flex-col items-center rounded-4 border border-dashed border-outline-gray-2 px-6 py-12 text-center text-base text-ink-gray-5"
  >
    <div v-if="icon" class="mb-3 grid size-10 place-items-center rounded-4 bg-surface-gray-2">
      <span :class="[icon, 'size-5 text-ink-gray-5']" aria-hidden="true" />
    </div>
    <div v-if="title" class="text-base-medium text-ink-gray-8">{{ title }}</div>
    <div v-if="description" class="mt-1 max-w-md text-p-base text-ink-gray-5">
      {{ description }}
    </div>
    <slot />
  </div>
</template>

<script lang="ts">
export type LucideIcon = `lucide-${string}`

/** What an empty list says about itself. Bind it with `v-bind` on `EmptyStateBox`. */
export interface EmptyState {
  icon: LucideIcon
  title: string
  description?: string
}
</script>

<script setup lang="ts">
// All optional: LoadError shows a description alone, and older callers still pass their
// whole content through the default slot.
defineProps<{
  icon?: LucideIcon
  title?: string
  description?: string
}>()
</script>
