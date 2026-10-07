<template>
  <div class="flex" v-if="space">
    <DiscussionView
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(space?.archived_at) || $readOnlyMode || publicVisitor"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DiscussionView from '@/components/DiscussionView.vue'
import { useSpace } from '@/data/spaces'
import { isPublicVisitor } from '@/utils/publicAccess'

interface Props {
  spaceId: string
  postId: string
  slug?: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
const publicVisitor = computed(() => isPublicVisitor())
</script>
