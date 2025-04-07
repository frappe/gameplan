<template>
  <div class="pb-16">
    <DiscussionList :filters="{ feed_type: 'bookmarks' }" :show-pinned="false" />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
</script>
