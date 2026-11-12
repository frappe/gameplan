<template>
  <ListRow :route="linkTo" :value="discussion.name" class="group h-[68px] sm:h-15">
    <ListCell>
      <UserAvatarWithHover :user="discussion.owner" size="2xl" />
    </ListCell>
    <ListCell>
      <div class="min-w-0 flex-1">
        <div class="flex min-w-0 items-center gap-1.5 leading-none text-ink-gray-8">
          <Tooltip v-if="pinned" text="Pinned">
            <PushPin class="size-3.5 shrink-0 text-ink-gray-5" role="img" aria-label="Pinned" />
          </Tooltip>
          <span
            class="overflow-hidden text-ellipsis whitespace-nowrap"
            :class="[
              discussion.unread ? 'text-md-semibold sm:text-base-semibold' : 'text-md sm:text-base',
            ]"
          >
            {{ discussion.title }}
          </span>
        </div>
        <div class="mt-1.5 flex min-w-0 items-center justify-between">
          <div
            class="inline-flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-md text-ink-gray-5 sm:text-base"
          >
            <div class="flex items-center min-w-0">
              <div class="text-ink-gray-5">
                <Tooltip v-if="discussion.closed_at" text="Closed">
                  <span class="lucide-lock size-4 p-[1px] mr-1" />
                </Tooltip>
                <Tooltip v-else-if="post.type == 'GP Comment'" text="Comment">
                  <span class="lucide-reply size-4 mr-1" />
                </Tooltip>
                <Tooltip v-else-if="post.type == 'GP Poll'" text="Poll">
                  <span class="lucide-align-left size-4 p-[1px] mr-1" />
                </Tooltip>
              </div>
              <div class="min-w-0 truncate">
                <span>
                  {{ $user(post.by).full_name.trim() }}
                </span>
                <span v-if="showSpaceName">
                  <span>&nbsp;in {{ placeLabel }}</span>
                  <span
                    v-if="isSpacePrivate(discussion.project)"
                    class="lucide-lock ml-0.5 inline-block h-3 w-3 align-[-1px] text-ink-gray-6"
                  /> </span
                >:&nbsp;
              </div>
              <div class="min-w-0 flex-1 truncate">
                {{ post.content }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ListCell>
    <ListCell class="justify-end">
      <!-- The remove button shares one grid cell with the date and badge and replaces them
           on hover or keyboard focus, so it reserves no width of its own. -->
      <div class="group/meta grid items-center justify-items-end">
        <div
          class="[grid-area:1/1]"
          :class="
            removable &&
            'group-hover:invisible group-has-[:focus-visible]/meta:invisible [@media(hover:none)]:invisible'
          "
        >
          <Tooltip :text="timestamp.tooltip">
            <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
              {{ relativeTimestamp(timestamp.at) }}
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
                <div v-if="discussion.comments_count + 1 === discussion.unread">
                  New unread post
                </div>
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
        <!-- Shares the grid cell with the time and count, so it takes no width. With a mouse
             it shows on row hover or focus; on touch screens it always shows, in their place.
             stop+prevent keep the click out of row navigation. -->
        <Tooltip v-if="removable" text="Remove bookmark">
          <Button
            variant="ghost"
            icon="lucide-bookmark-minus"
            label="Remove bookmark"
            class="[grid-area:1/1] transition-opacity focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:hover)]:opacity-0"
            @click.stop.prevent="emit('remove')"
          />
        </Tooltip>
      </div>
    </ListCell>
  </ListRow>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Tooltip, Badge, Button } from 'frappe-ui'
import { ListRow, ListCell } from 'frappe-ui/list'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import PushPin from './icons/PushPin.vue'
import { getCommunity } from '@/data/communities'
import { getSpace, useSpace } from '@/data/spaces'
import { Discussion } from '@/data/discussions'
import { fullTimestamp, relativeTimestamp } from '@/utils'

const props = defineProps<{
  discussion: Discussion
  showSpaceName: boolean
  showCommunityName?: boolean
  // Under "Newest created" the time on the right is when the discussion started, so the
  // order of the rows matches the times they show.
  showCreatedAt?: boolean
  // Adds a hover button that emits `remove` (the bookmarks list).
  removable?: boolean
  // Marks the row with a pin icon. Pinned rows lead the list with no heading.
  pinned?: boolean
}>()

const emit = defineEmits<{ remove: [] }>()

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

const timestamp = computed(() => {
  const at = props.showCreatedAt
    ? props.discussion.creation
    : post.value.at || props.discussion.creation
  const date = fullTimestamp(at)
  return { at, tooltip: props.showCreatedAt ? `Started ${date}` : date }
})

function isSpacePrivate(spaceId: string) {
  return useSpace(spaceId).value?.is_private
}
</script>
