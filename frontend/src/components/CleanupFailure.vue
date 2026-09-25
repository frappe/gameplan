<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-base p-6 text-ink-gray-9">
    <div class="flex max-w-md flex-col items-center gap-4 text-center">
      <span class="lucide-triangle-alert size-8 text-ink-gray-5" aria-hidden="true" />
      <div class="flex flex-col gap-2">
        <h1 class="text-md font-semibold text-ink-gray-9">Couldn't finish switching accounts</h1>
        <p class="text-p-base text-ink-gray-6">
          The previous account's data is still saved in this browser, so Gameplan has not opened.
          Reload to try again. If it keeps happening, close the app's other tabs first.
        </p>
      </div>
      <Button id="cleanup-retry" variant="solid" icon-left="lucide-refresh-cw" @click="reload">
        Reload
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'

function reload() {
  window.location.reload()
}
</script>
