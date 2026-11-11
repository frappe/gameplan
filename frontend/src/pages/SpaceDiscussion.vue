<template>
  <div class="flex" v-if="space">
    <!-- Keyed so opening another discussion mounts a fresh view instead of reusing this one -->
    <DiscussionView
      :key="postId"
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(space?.archived_at) || $readOnlyMode"
    />
  </div>
  <NotFound
    v-else-if="spaces.isFinished"
    title="Space not found"
    description="It may have been deleted, or you no longer have access to it."
  />
</template>

<script setup lang="ts">
import DiscussionView from '@/components/DiscussionView.vue'
import NotFound from '@/pages/NotFound.vue'
import { spaces, useSpace } from '@/data/spaces'

interface Props {
  spaceId: string
  postId: string
  slug?: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
</script>
