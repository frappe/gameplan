<template>
  <router-link
    :to="{
      name: 'Discussion',
      params: {
        spaceId: discussion.project,
        postId: discussion.name,
        slug: discussion.slug,
      },
    }"
    class="group relative block h-15 rounded-[10px] transition hover:bg-surface-gray-2"
  >
    <div class="flex h-full items-center space-x-4 overflow-hidden px-3 py-2">
      <UserInfo :email="discussion.owner">
        <template v-slot="{ user }">
          <div class="flex items-center space-x-3">
            <div class="relative flex">
              <UserAvatar :user="user.name" size="2xl" />
            </div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 items-center">
              <div
                v-if="discussion.unread"
                class="h-2 mr-1 w-2 shrink-0 rounded-full bg-orange-500"
              />
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap leading-none"
                :class="discussion.unread ? 'text-ink-gray-9' : 'text-ink-gray-9'"
              >
                <span
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-base"
                  :class="[discussion.unread ? 'font-semibold' : 'font-medium']"
                >
                  {{ discussion.title }}
                </span>
              </div>
            </div>
            <div class="mt-1.5 flex min-w-0 items-center justify-between">
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap text-base inline-flex items-center text-ink-gray-5"
              >
                <div class="flex items-center min-w-0">
                  <div class="text-ink-gray-5">
                    <Tooltip v-if="discussion.closed_at" text="Closed">
                      <LucideLock class="size-4 p-[1px] mr-1" />
                    </Tooltip>
                    <Tooltip v-else-if="discussion.last_post_type == 'GP Comment'" text="Comment">
                      <LucideReply class="size-4 mr-1" />
                    </Tooltip>
                    <Tooltip v-else-if="discussion.last_post_type == 'GP Poll'" text="Poll">
                      <LucideAlignLeft class="size-4 p-[1px] mr-1" />
                    </Tooltip>
                  </div>
                  <div>
                    <span>
                      {{ $user(discussion.last_post_by).full_name.trim() }}
                    </span>
                    <span class="inline-flex items-center" v-if="showSpaceName">
                      &nbsp;in {{ discussion.project_title }}
                      <LucideLock
                        v-if="isSpacePrivate(discussion.project)"
                        class="h-3 w-3 text-ink-gray-6 ml-0.5"
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
          <div class="ml-auto">
            <Tooltip :text="dayjs(discussion.last_post_at).format('D MMM YYYY [at] h:mm A')">
              <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
                {{ discussionTimestamp(discussion) }}
              </div>
            </Tooltip>
            <div class="mt-1.5 flex items-center justify-end space-x-3">
              <Tooltip text="Ongoing poll" v-if="discussion.ongoing_polls?.length">
                <LucideBarChart2 class="h-4 w-4 -rotate-90" />
              </Tooltip>
              <Badge>{{ (discussion.comments_count || 0) + 1 }}</Badge>
            </div>
          </div>
        </template>
      </UserInfo>
    </div>
    <!-- Separator -->
    <div
      class="mx-3 h-px border-t border-outline-gray-modals transition-opacity group-hover:opacity-0"
      v-if="index < total - 1"
    ></div>
  </router-link>
</template>
<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { dayjs } from '@/utils/dayjs'
import UserAvatar from './UserAvatar.vue'
import UserInfo from './UserInfo.vue'
import { useSpace } from '@/data/spaces'
import { Discussion } from '@/data/discussions'

import LucideReply from '~icons/lucide/reply'
import LucideBarChart2 from '~icons/lucide/bar-chart-2'
import LucideLock from '~icons/lucide/lock'
import LucideAlignLeft from '~icons/lucide/align-left'

const props = defineProps<{
  discussion: Discussion
  index: number
  total: number
  showSpaceName: boolean
}>()

function discussionTimestamp(d) {
  let timestamp = d.last_post_at || d.creation
  if (dayjs().diff(timestamp, 'day') < 3) {
    return dayjs(timestamp).fromNow()
  }
  if (dayjs().diff(timestamp, 'year') < 1) {
    return dayjs(timestamp).format('D MMM')
  }
  return dayjs(timestamp).format('D MMM YYYY')
}

function isSpacePrivate(spaceId: string) {
  return useSpace(spaceId).value?.is_private
}
</script>
