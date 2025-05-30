<template>
  <div class="relative flex h-full flex-col" v-if="users.isFinished">
    <div class="h-full flex-1">
      <div class="flex h-full">
        <ScrollAreaRoot class="relative block min-h-0 flex-shrink-0">
          <slot name="sidebar" />
          <AppSidebar />
        </ScrollAreaRoot>
        <ScrollContainer>
          <div
            v-if="$readOnlyMode"
            class="right-0 top-0 mb-3 bg-surface-gray-2 py-3 text-sm text-ink-gray-5"
          >
            <div class="mx-auto px-10">
              This site is running in read-only mode. Full functionality will be restored soon.
            </div>
          </div>
          <slot />
        </ScrollContainer>
      </div>
    </div>
    <CommandPalette />
    <SettingsDialog />
  </div>
</template>
<script setup lang="ts">
import { ScrollAreaRoot } from 'reka-ui'
import ScrollContainer from './ScrollContainer.vue'
import AppSidebar from './AppSidebar.vue'
import CommandPalette from './CommandPalette/CommandPalette.vue'
import SettingsDialog from './Settings/SettingsDialog.vue'
import { users } from '@/data/users'
</script>
