<template>
  <PageHeaderShell
    base-class="z-10 flex min-h-12 flex-col justify-center border-b px-3 sm:px-5"
  >
    <div class="flex items-center justify-between">
      <slot></slot>
    </div>
  </PageHeaderShell>
</template>

<script setup lang="ts">
import PageHeaderShell from './PageHeaderShell.vue'
</script>
