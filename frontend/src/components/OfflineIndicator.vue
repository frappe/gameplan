<template>
  <!-- Teleported + fixed to the true viewport top so it renders above both
       MobileShell and DesktopShell (frappe-ui), not inside either one - see the
       `data-offline` attribute this sets below and the matching `[data-slot=...]`
       rules in index.css, which push the shells' own content down by exactly this
       banner's height. That's what keeps it from ever overlapping the header,
       search, nav, or anything else already on screen, instead of covering it. -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-full"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0 -translate-y-full"
    >
      <div
        v-if="!isOnline"
        role="status"
        class="fixed inset-x-0 top-0 z-[60] flex h-[var(--offline-banner-height)] items-center justify-center gap-1.5 bg-surface-gray-3 px-3 text-p-sm text-ink-gray-7"
      >
        <span class="lucide-wifi-off size-3.5 shrink-0" aria-hidden="true" />
        <span class="font-medium text-ink-gray-8">Offline</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { isOnline } from '@/data/online'

// A DOM attribute, not a Vue-scoped style: the shells this needs to push down
// (MobileShell.vue, DesktopShell.vue) live in frappe-ui, outside this component's
// own render tree, so index.css targets them by this attribute + their own
// `data-slot` hooks instead.
watch(
  isOnline,
  (online) => {
    document.documentElement.toggleAttribute('data-offline', !online)
  },
  { immediate: true },
)
</script>
