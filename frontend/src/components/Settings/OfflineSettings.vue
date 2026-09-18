<template>
  <SettingsHeader>
    <h2 class="text-lg-semibold text-ink-gray-8">Offline</h2>
  </SettingsHeader>

  <SettingsBody>
    <OfflineSettingsPanel class="pt-6" />
  </SettingsBody>
</template>

<script setup lang="ts">
import { SettingsBody, SettingsHeader } from 'frappe-ui'
import OfflineSettingsPanel from './OfflineSettingsPanel.vue'
</script>
