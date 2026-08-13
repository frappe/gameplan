<template>
  <ScrollAreaRoot class="relative block min-h-0 flex-1">
    <ScrollAreaViewport class="h-full w-full isolate overflow-auto" id="scrollContainer">
      <slot />
    </ScrollAreaViewport>
    <ScrollBar />
  </ScrollAreaRoot>
</template>
<script setup lang="ts">
import { ScrollAreaRoot, ScrollAreaViewport } from 'reka-ui'
import ScrollBar from './ScrollBar.vue'
</script>
