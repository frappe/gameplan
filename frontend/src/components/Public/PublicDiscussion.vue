<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
    <router-link
      v-if="space"
      :to="{ name: 'SpaceDiscussions', params: { communityId: space.team, spaceId } }"
      class="inline-flex items-center gap-1 text-sm text-ink-gray-5 hover:text-ink-gray-7"
    >
      <span class="lucide-arrow-left size-3.5" aria-hidden="true" />
      {{ space.title }}
    </router-link>

    <article v-if="discussion" class="mt-3">
      <h1 class="text-2xl-semibold text-ink-gray-9">{{ discussion.title }}</h1>
      <PublicAuthor class="mt-3" :user="discussion.owner || ''" :timestamp="discussion.creation" />
      <PublicContent class="mt-4" :content="discussion.content" />
      <PublicReactions class="mt-3" :reactions="discussion.reactions" />
      <div
        v-if="discussion.closed_at"
        class="mt-4 rounded bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-6"
      >
        This discussion is closed.
      </div>
    </article>

    <div v-if="posts.length" class="mt-8 space-y-6 border-t border-outline-gray-1 pt-6">
      <div v-for="post in posts" :key="`${post.kind}:${post.row.name}`">
        <PublicPoll v-if="post.kind === 'poll'" :poll="post.row" />
        <div v-else>
          <PublicAuthor :user="post.row.owner || ''" :timestamp="post.row.creation" />
          <div v-if="post.row.deleted_at" class="mt-2 text-p-base italic text-ink-gray-5">
            This message is deleted
          </div>
          <template v-else>
            <PublicContent class="mt-2" :content="post.row.content" />
            <PublicReactions class="mt-2" :reactions="post.row.reactions" />
          </template>
        </div>
      </div>
    </div>

    <PublicJoinPrompt v-if="discussion" class="mt-8" :title="joinTitle" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDoc, useList } from 'frappe-ui'
import { getSpace } from '@/data/spaces'
import { publicListUrl } from '@/utils/publicAccess'
import PublicAuthor from './PublicAuthor.vue'
import PublicContent from './PublicContent.vue'
import PublicJoinPrompt from './PublicJoinPrompt.vue'
import PublicPoll, { type PublicPollRow } from './PublicPoll.vue'
import PublicReactions from './PublicReactions.vue'

const props = defineProps<{ spaceId: string; postId: string }>()

const space = computed(() => getSpace(props.spaceId))

interface PublicDiscussionDoc {
  name: string
  title: string
  owner: string | null
  creation: string
  content: string
  closed_at: string | null
  reactions: { emoji: string }[]
}

interface PublicCommentRow {
  name: string
  owner: string | null
  creation: string
  content: string
  deleted_at: string | null
  reactions: { emoji: string }[]
}

// Every request here is one the server answers for someone who is not signed in, with
// authors as profile handles and no member, voter or reactor identities in the rows.
const discussionDoc = useDoc<PublicDiscussionDoc>({
  doctype: 'GP Discussion',
  name: props.postId,
})
const discussion = computed(() => discussionDoc.doc)

const comments = useList<PublicCommentRow>({
  doctype: 'GP Comment',
  url: publicListUrl('GP Comment'),
  fields: ['name', 'owner', 'creation', 'content', 'deleted_at', { reactions: ['name', 'emoji'] }],
  filters: { reference_doctype: 'GP Discussion', reference_name: props.postId },
  orderBy: 'creation asc',
  limit: 999,
  immediate: true,
})

const polls = useList<PublicPollRow>({
  doctype: 'GP Poll',
  url: publicListUrl('GP Poll'),
  fields: [
    'name',
    'title',
    'owner',
    'creation',
    'stopped_at',
    'total_votes',
    { options: ['name', 'title', 'idx', 'percentage'] },
    { reactions: ['name', 'emoji'] },
  ],
  filters: { discussion: props.postId },
  orderBy: 'creation asc',
  limit: 999,
  immediate: true,
})

type Post = { kind: 'comment'; row: PublicCommentRow } | { kind: 'poll'; row: PublicPollRow }

const posts = computed<Post[]>(() =>
  [
    ...(comments.data || []).map((row) => ({ kind: 'comment' as const, row })),
    ...(polls.data || []).map((row) => ({ kind: 'poll' as const, row })),
  ].sort((a, b) => a.row.creation.localeCompare(b.row.creation)),
)

const joinTitle = computed(() =>
  discussion.value?.closed_at ? 'Follow this community' : 'Join the conversation',
)
</script>
