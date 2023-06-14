<template>
  <div class="flex">
    <div class="h-full w-full py-6">
      <div class="mb-5 flex items-center justify-between">
        <h2 class="text-2xl font-semibold">Posts</h2>
      </div>
      <DiscussionList
        class="-mx-5 sm:mx-0"
        :listOptions="{ filters: { team: team.doc.name } }"
        routeName="ProjectDiscussion"
      />
    </div>
  </div>
</template>
<script setup>
import DiscussionList from '@/components/DiscussionList.vue'
defineProps(['team'])
</script>
