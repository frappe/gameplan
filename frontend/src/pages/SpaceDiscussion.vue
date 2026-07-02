<template>
  <div class="flex" v-if="space">
    <DiscussionView
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(space?.archived_at) || readOnlyMode || session.canBrowsePublicWeb"
    />
  </div>
</template>

<script setup lang="ts">
import DiscussionView from '@/components/DiscussionView.vue'
import { session } from '@/data/session'
import { useSpace } from '@/data/spaces'

interface Props {
  spaceId: string
  postId: string
  slug?: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
const readOnlyMode = Boolean(window.read_only_mode)
</script>
