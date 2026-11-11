<template>
  <div
    ref="fade"
    aria-hidden="true"
    class="pointer-events-none absolute inset-x-0 top-full h-8 bg-gradient-to-b from-surface-base/60 via-surface-base/20 via-40% to-transparent transition-opacity duration-150 print:hidden"
    :class="isStuck ? 'opacity-100' : 'opacity-0'"
  />
</template>

<script setup lang="ts">
// Place inside a sticky row. While the row is pinned to the top of the shell scroller,
// a soft fade under it shades the line where the content scrolls out of sight. It starts
// below full opacity and eases out, so it reads as a shadow rather than a band.
import { computed, ref, useTemplateRef } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'
import { shellScrollContainer, useShellScrolled } from 'frappe-ui'

const fade = useTemplateRef<HTMLElement>('fade')
const row = computed(() => fade.value?.parentElement ?? null)
const touchesTop = ref(false)
// A row that starts at the very top of the scroller touches it before any scroll,
// so it only counts as stuck once the page has moved.
const isScrolled = useShellScrolled({ threshold: 0 })
const isStuck = computed(() => touchesTop.value && isScrolled.value)

// The 1px top margin shrinks the root, so a row pinned at the scroller's edge reads
// as cut off at the top, while a row that is merely in view reads as whole.
useIntersectionObserver(
  row,
  ([entry]) => {
    const rootTop = entry.rootBounds?.top ?? 0
    touchesTop.value = entry.intersectionRatio < 1 && entry.boundingClientRect.top < rootTop
  },
  { root: shellScrollContainer, rootMargin: '-1px 0px 0px 0px', threshold: [0, 1] },
)
</script>
