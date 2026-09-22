<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-base p-6 text-ink-gray-9">
    <div class="max-w-md text-center">
      <h1 class="mb-2 text-lg font-semibold text-ink-gray-9">Couldn't finish switching accounts</h1>
      <p class="mb-5 text-p-base text-ink-gray-6">
        The previous account's data is still saved in this browser, so Gameplan has not opened.
        Reload to try again. If it keeps happening, close the app's other tabs first.
      </p>
      <Button id="cleanup-retry" variant="solid" @click="reload"> Reload </Button>
    </div>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'

function reload() {
  window.location.reload()
}
</script>
