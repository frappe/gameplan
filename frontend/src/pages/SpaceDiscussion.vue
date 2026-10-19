<template>
  <div class="flex flex-col" v-if="space">
    <p
      v-if="isCommunityBanned(space?.team, useSessionUser())"
      class="p-4 text-base text-ink-gray-5"
    >
      You are banned from participating in this Community. You can still read accessible content.
    </p>
    <!-- Keyed so opening another discussion mounts a fresh view instead of reusing this one -->
    <DiscussionView
      :key="postId"
      class="w-full"
      :postId="postId"
      :read-only-mode="
        Boolean(space?.archived_at) ||
        $readOnlyMode ||
        publicVisitor ||
        isCommunityBanned(space?.team, useSessionUser())
      "
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isCommunityBanned } from '@/utils/permissions'
import { useSessionUser } from '@/data/users'
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
