<template>
  <PageHeaderMobile title="Offline">
    <template #prefix>
      <PageHeaderBackButton :to="{ name: 'More' }" />
    </template>
  </PageHeaderMobile>
  <div class="px-4 pb-28 pt-4">
    <OfflineSettingsPanel />
  </div>
</template>

<script setup lang="ts">
import { PageHeaderBackButton, PageHeaderMobile, usePageMeta } from 'frappe-ui'
import OfflineSettingsPanel from '@/components/Settings/OfflineSettingsPanel.vue'

usePageMeta(() => ({ title: 'Offline' }))
</script>
