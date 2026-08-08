<template>
  <!-- Top-center, out of the way of the comment composer (bottom) and the dev
       user switcher (bottom-left). Teleported to body so it sits above any
       page-local `overflow-hidden`/`relative` ancestor. -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="!isOnline"
        class="pointer-events-none fixed inset-x-0 top-2 z-50 flex justify-center"
      >
        <div
          class="pointer-events-auto flex items-center gap-2 rounded-full bg-surface-gray-8 px-3 py-1.5 text-sm text-ink-white shadow-lg"
        >
          <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-surface-gray-4"></span>
          You're offline — showing saved content
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { isOnline } from '@/data/online'
</script>
