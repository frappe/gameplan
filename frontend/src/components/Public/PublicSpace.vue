<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <div v-if="space" class="mb-6">
      <div class="text-sm text-ink-gray-5">{{ community?.title }}</div>
      <h1 class="mt-1 flex items-center gap-2 text-2xl-semibold text-ink-gray-9">
        <SpaceIcon :icon="space.icon" class="size-5 text-ink-gray-6" />
        {{ space.title }}
      </h1>
    </div>

    <div v-if="discussions.data?.length" class="divide-y divide-outline-gray-1">
      <router-link
        v-for="discussion in discussions.data"
        :key="discussion.name"
        :to="{
          name: 'Discussion',
          params: {
            communityId: space?.team,
            spaceId,
            postId: discussion.name,
            slug: discussion.slug,
          },
        }"
        class="block py-4 hover:bg-surface-gray-1 sm:-mx-3 sm:rounded sm:px-3"
      >
        <div class="text-lg-semibold text-ink-gray-9">{{ discussion.title }}</div>
        <div
          v-if="discussion.last_comment_content"
          class="mt-1 line-clamp-2 text-p-base text-ink-gray-6"
        >
          {{ discussion.last_comment_content }}
        </div>
        <div class="mt-2 flex items-center gap-3 text-sm text-ink-gray-5">
          <PublicAuthor
            :user="discussion.owner || ''"
            :timestamp="discussion.last_post_at"
            size="sm"
          />
          <span v-if="discussion.comments_count" class="flex items-center gap-1">
            <span class="lucide-message-square size-3.5" aria-hidden="true" />
            {{ discussion.comments_count }}
          </span>
        </div>
      </router-link>
    </div>
    <div v-else-if="discussions.isFinished" class="py-10 text-center text-p-base text-ink-gray-5">
      Nothing has been posted here yet.
    </div>

    <div v-if="discussions.hasNextPage" class="mt-4 flex justify-center">
      <Button label="Load more" :loading="discussions.loading" @click="discussions.next()" />
    </div>

    <PublicJoinPrompt v-if="discussions.isFinished" class="mt-8" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, useList } from 'frappe-ui'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { getCommunity } from '@/data/communities'
import { getSpace } from '@/data/spaces'
import PublicAuthor from './PublicAuthor.vue'
import PublicJoinPrompt from './PublicJoinPrompt.vue'

const props = defineProps<{ spaceId: string }>()

const space = computed(() => getSpace(props.spaceId))
const community = computed(() => (space.value?.team ? getCommunity(space.value.team) : null))

interface PublicDiscussionRow {
  name: string
  title: string
  slug: string
  owner: string | null
  last_post_at: string
  comments_count: number
  last_comment_content?: string
}

const discussions = useList<PublicDiscussionRow>({
  url: '/api/v2/method/gameplan.gameplan.doctype.gp_discussion.api.get_discussions',
  doctype: 'GP Discussion',
  filters: { project: props.spaceId },
  orderBy: 'last_post_at desc',
  limit: 30,
  immediate: true,
})
</script>
