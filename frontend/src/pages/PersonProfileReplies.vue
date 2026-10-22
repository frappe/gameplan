<template>
  <div class="pb-16 -mx-3">
    <DiscussionList
      :filters="() => ({ participator: profile.doc?.user })"
      :cacheKey="`PersonReplies-${personId}`"
      :key="personId"
      :show-pinned="false"
    />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfileReplies',
})

defineProps<{
  profile: { doc?: GPUserProfile | null }
  personId: string
}>()
</script>
