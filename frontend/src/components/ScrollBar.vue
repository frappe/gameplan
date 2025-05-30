<template>
  <ScrollAreaScrollbar
    class="flex select-none touch-none p-0.5 z-20 bg-transparent transition-colors duration-150 ease-out hover:bg-black/5 dark:hover:bg-white/5 data-[orientation=vertical]:w-2.5 data-[orientation=horizontal]:flex-col data-[orientation=horizontal]:h-2.5"
    orientation="vertical"
  >
    <ScrollAreaThumb
      class="flex-1 bg-gray-400 dark:bg-gray-700 rounded-lg relative before:content-[''] before:absolute before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:w-full before:h-full before:min-w-[44px] before:min-h-[44px]"
    />
  </ScrollAreaScrollbar>
</template>
<script setup lang="ts">
import { ScrollAreaScrollbar, ScrollAreaThumb } from 'reka-ui'
</script>
