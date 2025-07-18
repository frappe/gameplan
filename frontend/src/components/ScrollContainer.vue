<template>
  <ScrollAreaViewport class="w-full isolate overflow-auto bg-surface-white" id="scrollContainer">
    <slot />
  </ScrollAreaViewport>
  <ScrollBar />
</template>
<script setup lang="ts">
import { ScrollAreaViewport } from 'reka-ui'
import ScrollBar from './ScrollBar.vue'
</script>
