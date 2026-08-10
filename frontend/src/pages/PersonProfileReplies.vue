<template>
  <div class="pb-16 -mx-3">
    <DiscussionList
      ref="discussionListRef"
      v-show="!listFailure"
      :filters="() => ({ participator: profile.doc?.user })"
      :cacheKey="`PersonReplies-${personId}`"
      :show-pinned="false"
    />
    <!-- The fetch failed and there's no cached page to fall back to (staleOnError already
         covers the case where cached data exists). Without this a failed fetch renders as
         an empty list - indistinguishable from someone who has genuinely never replied. -->
    <OfflineContentFallback
      v-if="listFailure"
      class="mx-auto mt-6 max-w-2xl px-6"
      :title="listFailure.title"
      :message="listFailure.message"
      @retry="discussionsResource?.reload()"
    />
  </div>
</template>
<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import DiscussionList from '@/components/DiscussionList.vue'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'
import { isBrowserOffline, isNetworkError } from '@/offline'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfileReplies',
})

defineProps<{
  profile: { doc?: GPUserProfile | null }
  personId: string
}>()

const discussionListRef = useTemplateRef('discussionListRef')
const discussionsResource = computed(() => discussionListRef.value?.discussions)
const listFailure = computed(() => {
  const discussions = discussionsResource.value
  if (!discussions) return null
  const failed =
    discussions.isFinished && !discussions.loading && discussions.error && discussions.data == null
  if (!failed) return null

  const offline = isBrowserOffline() || isNetworkError(discussions.error)
  return offline
    ? {
        title: "Can't load this while offline",
        message: "This person's replies haven't been saved for offline use yet.",
      }
    : {
        title: 'Could not load replies',
        message: 'Something went wrong while loading this list. Retry to try again.',
      }
})
</script>
