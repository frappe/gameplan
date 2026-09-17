<template>
  <div class="pb-16 -mx-3">
    <DiscussionList
      :filters="() => ({ owner: profile.doc?.user })"
      :cacheKey="`PersonPosts-${personId}`"
      :key="personId"
      :showPinned="false"
    />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfilePosts',
})

defineProps<{
  profile: { doc?: GPUserProfile | null }
  personId: string
}>()
</script>
