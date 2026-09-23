<template>
  <!-- Above both frappe-ui shells rather than inside one; index.css pushes their
       content down by the banner's height so it never covers the header. -->
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
import { useEventListener } from '@vueuse/core'
import { toast } from 'frappe-ui'
import { isOnline } from '@/data/online'
import { OFFLINE_ACTION_MESSAGE } from '@/data/loadFailure'

// An attribute on <html>, since the shells it pushes down live in frappe-ui.
watch(
  isOnline,
  (online) => {
    document.documentElement.toggleAttribute('data-offline', !online)
  },
  { immediate: true },
)

// Controls are disabled while offline, and a disabled button gives no feedback on its own.
// Pointer events (unlike clicks) still reach disabled elements, so one listener covers
// every button, menu item and reaction in the app.
const DISABLED_CONTROL = ':disabled, [aria-disabled="true"], [data-disabled]'

useEventListener(
  document,
  'pointerup',
  (event) => {
    if (isOnline.value || !(event.target instanceof Element)) return
    if (!event.target.closest(DISABLED_CONTROL)) return
    toast.warning(OFFLINE_ACTION_MESSAGE, { id: 'offline-action' })
  },
  { capture: true },
)
</script>
