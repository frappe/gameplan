<template>
  <ListRow :to="linkTo" :value="discussion.name" class="h-[68px] sm:h-15">
    <ListCell>
      <UserAvatarWithHover :user="discussion.owner" size="2xl" />
    </ListCell>
    <ListCell>
      <div class="min-w-0 flex-1">
        <div class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-ink-gray-8">
          <span
            class="overflow-hidden text-ellipsis whitespace-nowrap"
            :class="[
              discussion.unread ? 'text-lg-semibold sm:text-base-semibold' : 'text-lg sm:text-base',
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
                <Tooltip v-else-if="discussion.last_post_type == 'GP Comment'" text="Comment">
                  <span class="lucide-reply size-4 mr-1" />
                </Tooltip>
                <Tooltip v-else-if="discussion.last_post_type == 'GP Poll'" text="Poll">
                  <span class="lucide-align-left size-4 p-[1px] mr-1" />
                </Tooltip>
              </div>
              <div>
                <span>
                  {{ $user(discussion.last_post_by || discussion.owner).full_name.trim() }}
                </span>
                <span class="inline-flex items-center" v-if="showSpaceName">
                  &nbsp;in {{ discussion.project_title }}
                  <span
                    v-if="isSpacePrivate(discussion.project)"
                    class="lucide-lock h-3 w-3 text-ink-gray-6 ml-0.5"
                  /> </span
                >:&nbsp;
              </div>
              <div class="truncate">
                {{ discussion.last_comment_content || discussion.last_poll_title }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </ListCell>
    <ListCell class="justify-end">
      <div>
        <Tooltip :text="dayjsLocal(discussion.last_post_at).format('D MMM YYYY [at] h:mm A')">
          <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
            {{ relativeTimestamp(discussion.last_post_at || discussion.creation) }}
          </div>
        </Tooltip>
        <div class="mt-1.5 flex items-center justify-end space-x-3">
          <Tooltip text="Ongoing poll" v-if="discussion.ongoing_polls?.length">
            <span class="lucide-bar-chart-2 h-4 w-4 -rotate-90" />
          </Tooltip>
          <Tooltip v-if="discussion.unread">
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
import { getSpace, useSpace } from '@/data/spaces'
import { Discussion } from '@/data/discussions'
import { relativeTimestamp } from '@/utils'

const props = defineProps<{
  discussion: Discussion
  showSpaceName: boolean
}>()

const linkTo = computed(() => {
  return {
    name: 'Discussion',
    params: {
      communityId: getSpace(props.discussion.project)?.team,
      spaceId: props.discussion.project,
      postId: props.discussion.name,
      slug: props.discussion.slug,
    },
  }
})

function isSpacePrivate(spaceId: string) {
  return useSpace(spaceId).value?.is_private
}
</script>
