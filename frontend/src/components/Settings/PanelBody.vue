<template>
  <!-- The panel's scrolling region. In the dialog that is frappe-ui's SettingsBody,
       which brings its own ScrollArea and wide insets. A phone renders the panel as
       a page inside MobileShell, which already scrolls natively, so the body is a
       plain page container — no nested scroller, no dialog insets to undo. -->
  <SettingsBody v-if="!isPhone">
    <slot />
  </SettingsBody>
  <!-- pb-16 is SettingsBody's own bottom padding, kept so a panel ends the same
       way in either shell. -->
  <div v-else class="body-container pb-16">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { SettingsBody } from 'frappe-ui'
import { useIsMobile } from '@/utils/useIsMobile'

const isPhone = useIsMobile()
</script>
