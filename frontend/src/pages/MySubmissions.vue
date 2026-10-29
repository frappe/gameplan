<template>
  <div class="body-container py-5">
    <h1 class="text-xl-semibold text-ink-gray-9">My submissions</h1>
    <p class="mt-3 text-base text-ink-gray-6">
      Track submissions awaiting approval, read moderator feedback, and open approved posts.
    </p>
    <ApprovalQueue />
  </div>
</template>
<script setup lang="ts">
import ApprovalQueue from '@/components/ApprovalQueue.vue'
</script>
