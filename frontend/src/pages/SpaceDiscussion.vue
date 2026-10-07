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
</template>

<script setup lang="ts">
import DiscussionView from '@/components/DiscussionView.vue'
import { useSpace } from '@/data/spaces'

interface Props {
  spaceId: string
  postId: string
  slug?: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
</script>
