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
              <UserAvatar :user="discussion.closed_by || user.name" size="2xl" />
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
                <Badge variant="outline" theme="green" class="mr-1" v-if="discussion.closed_at">
                  Closed
                </Badge>
                <span class="sm:inline">
                  {{ user.full_name }}
                  <span v-if="showSpaceName"> in {{ discussion.project_title }} </span>
                </span>
              </div>
            </div>
          </div>
          <div class="ml-auto">
            <div
              class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5"
              :title="discussionTimestampDescription(discussion)"
            >
              {{ discussionTimestamp(discussion) }}
            </div>
            <div class="mt-1.5 flex items-center justify-end space-x-3">
              <Tooltip text="Ongoing poll" v-if="discussion.ongoing_polls?.length">
                <LucideBarChart2 class="h-4 w-4 -rotate-90" />
              </Tooltip>
              <Badge>{{ discussion.comments_count + 1 }}</Badge>
            </div>
          </div>
        </template>
      </UserInfo>
    </div>
    <div class="mx-3 h-px border-t border-outline-gray-modals" v-if="index < total - 1"></div>
  </router-link>
</template>
<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import dayjs from '@/utils/dayjs'
import UserAvatar from './UserAvatar.vue'
import UserInfo from './UserInfo.vue'

import LucidePin from '~icons/lucide/pin'

const props = defineProps<{
  discussion: Object
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

function discussionTimestampDescription(d) {
  return [`First Post: ${dayjs(d.creation)}`, `Latest Post: ${dayjs(d.last_post_at)}`].join('\n')
}
</script>
