<template>
  <div class="pb-16">
    <DiscussionList :filters="{ user_bookmarks: true }" :show-pinned="false" />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
</script>
