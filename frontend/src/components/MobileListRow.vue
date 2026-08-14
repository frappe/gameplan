<template>
  <button
    type="button"
    class="block w-full text-start transition active:bg-surface-gray-2"
    :class="active ? 'bg-surface-gray-2' : ''"
  >
    <!--
      The flex layout lives on this inner wrapper, not the <button>. iOS Safari (WebKit)
      wraps a button's children in an anonymous box, so making the button itself a flex
      container leaves the rows top-aligned instead of vertically centered.
    -->
    <span class="flex w-full items-stretch" :class="rowHeightClass">
      <span class="flex shrink-0 items-center py-2.5 ps-4 pe-3">
        <slot name="icon" />
      </span>
      <span class="relative flex min-w-0 flex-1 items-center gap-3 py-2.5 pe-4">
        <span
          v-if="border"
          class="pointer-events-none absolute left-0 right-4 top-0 border-t"
          aria-hidden="true"
        />
        <span class="min-w-0 flex-1 truncate text-lg text-ink-gray-9">
          <slot />
        </span>
        <slot name="trailing" />
      </span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    border?: boolean
    height?: 'fixed' | 'min'
    active?: boolean
  }>(),
  {
    border: false,
    height: 'min',
    active: false,
  },
)

const rowHeightClass = computed(() => (props.height === 'fixed' ? 'h-12' : 'min-h-12'))
</script>
