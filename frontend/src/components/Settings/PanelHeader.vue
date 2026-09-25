<template>
  <!-- The panel's fixed (non-scrolling) region. In the dialog that is frappe-ui's
       SettingsHeader. On a phone the panel is a page whose own header already names
       the tab (pages/SettingsPage.vue), so the title is dropped and only the
       controls — search, filters, actions — are drawn. -->
  <SettingsHeader v-if="!isPhone">
    <div v-if="title" class="flex flex-col gap-4">
      <h2 class="text-md-semibold text-ink-gray-8">{{ title }}</h2>
      <slot />
    </div>
    <slot v-else />
  </SettingsHeader>
  <div v-else-if="$slots.default" class="body-container pt-4">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { SettingsHeader } from 'frappe-ui'
import { useIsMobile } from '@/utils/useIsMobile'

defineProps<{
  /**
   * Heading for the dialog, drawn above the default slot. Phones take the title from
   * the page header instead. A panel whose header needs its own layout omits this and
   * keeps its own heading (hidden below `sm`) inside the slot.
   */
  title?: string
}>()

defineSlots<{
  /** Controls that belong beside the heading and stay on a phone. */
  default?: () => any
}>()

const isPhone = useIsMobile()
</script>
