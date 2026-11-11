<template>
  <ListRow :route="linkTo" :value="discussion.name" class="h-[68px] sm:h-15">
    <ListCell>
      <UserAvatarWithHover :user="discussion.owner" size="2xl" />
    </ListCell>
    <ListCell>
      <div class="min-w-0 flex-1">
        <div class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-ink-gray-8">
          <span
            class="overflow-hidden text-ellipsis whitespace-nowrap"
            :class="[
              discussion.unread ? 'text-md-semibold sm:text-base-semibold' : 'text-md sm:text-base',
            ]"
          >
            {{ discussion.title }}
          </span>
        </div>
        <div class="mt-1.5 flex min-w-0 items-center text-md text-ink-gray-5 sm:text-base">
          <Tooltip v-if="discussion.closed_at" text="Closed">
            <span class="lucide-lock size-4 shrink-0 p-[1px] mr-1" />
          </Tooltip>
          <Tooltip v-else-if="post.type == 'GP Comment'" text="Comment">
            <span class="lucide-reply size-4 shrink-0 mr-1" />
          </Tooltip>
          <Tooltip v-else-if="post.type == 'GP Poll'" text="Poll">
            <span class="lucide-align-left size-4 shrink-0 p-[1px] mr-1" />
          </Tooltip>
          <!-- One run of text, so a long author or space name pushes the post out of view
               and the line ends in a single ellipsis, not a stub of the post's first letter. -->
          <p class="min-w-0 truncate">
            <span>{{ $user(post.by).full_name.trim() }}</span>
            <span v-if="showSpaceName">&nbsp;in {{ placeLabel }}</span>
            <span
              v-if="showSpaceName && isSpacePrivate(discussion.project)"
              class="lucide-lock ml-0.5 inline-block h-3 w-3 align-[-1px] text-ink-gray-6"
            />
            <span>:&nbsp;{{ post.content }}</span>
          </p>
        </div>
      </div>
    </ListCell>
    <ListCell class="justify-end">
      <div>
        <Tooltip :text="postTime.format('D MMM YYYY [at] h:mm A')">
          <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
            {{ relativeTimestamp(postTime) }}
          </div>
        </Tooltip>
        <div class="mt-1.5 flex items-center justify-end space-x-3">
          <Tooltip text="Ongoing poll" v-if="discussion.ongoing_polls?.length">
            <span class="lucide-bar-chart-2 h-4 w-4 -rotate-90" />
          </Tooltip>
          <Tooltip v-if="discussion.unread">
            <!-- Amber is deliberate and owner-requested. Known AA trade: white on amber-600 is
                 about 3.22:1, below the 4.5:1 floor. Do not swap it for a gray Badge. -->
            <div
              class="bg-amber-600 dark:bg-dark-amber-500 text-white rounded-full h-4 min-w-4 px-1 grid place-content-center text-xs"
            >
              {{ discussion.unread }}
            </div>
            <template #content>
              <div v-if="discussion.comments_count + 1 === discussion.unread">New unread post</div>
              <div v-else-if="discussion.comments_count > 0" class="p-0.5">
                <div>{{ discussion.unread }} unread</div>
                <div class="text-ink-gray-3 mt-0.5">
                  {{ discussion.comments_count }}
                  {{ discussion.comments_count == 1 ? 'comment' : 'comments' }}
                </div>
              </div>
            </template>
          </Tooltip>
          <Badge v-else>{{ (discussion.comments_count || 0) + 1 }}</Badge>
        </div>
      </div>
    </ListCell>
  </ListRow>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Tooltip, Badge, dayjsLocal } from 'frappe-ui'
import { ListRow, ListCell } from 'frappe-ui/list'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { getCommunity } from '@/data/communities'
import { getSpace, useSpace } from '@/data/spaces'
import { Discussion } from '@/data/discussions'
import { relativeTimestamp } from '@/utils'

const props = defineProps<{
  discussion: Discussion
  showSpaceName: boolean
  showCommunityName?: boolean
}>()

const placeLabel = computed(() => {
  if (!props.showCommunityName) return props.discussion.project_title
  const communityId = getSpace(props.discussion.project)?.team
  const communityTitle = communityId ? getCommunity(communityId)?.title : undefined
  return [communityTitle, props.discussion.project_title].filter(Boolean).join(' / ')
})

const linkTo = computed(() => {
  return {
    name: 'Discussion',
    params: {
      communityId: getSpace(props.discussion.project)?.team,
      spaceId: props.discussion.project,
      postId: props.discussion.name,
      slug: props.discussion.slug,
    },
    query: props.discussion.bookmark
      ? { comment: props.discussion.bookmarked_comment || 'first_post' }
      : undefined,
  }
})

const post = computed(() => {
  const d = props.discussion
  if (d.bookmark) {
    return {
      type: d.bookmarked_comment ? 'GP Comment' : null,
      by: d.bookmarked_post_by,
      content: d.bookmarked_post_content,
      at: d.bookmarked_post_at,
    }
  }
  return {
    type: d.last_post_type,
    by: d.last_post_by || d.owner,
    content: d.last_comment_content || d.last_poll_title,
    at: d.last_post_at,
  }
})

// Parsed once: a list renders many rows, and each timezone conversion is slow.
const postTime = computed(() => dayjsLocal(post.value.at || props.discussion.creation))

function isSpacePrivate(spaceId: string) {
  return useSpace(spaceId).value?.is_private
}
</script>
