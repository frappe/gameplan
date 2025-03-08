<template>
  <HoverCardRoot v-model:open="userCardOpen">
    <HoverCardTrigger asChild>
      <UserAvatar :user="user" v-bind="$attrs" />
    </HoverCardTrigger>
    <HoverCardPortal>
      <HoverCardContent side="top" class="z-50 w-66">
        <HoverCardArrow class="fill-surface-white" />
        <div class="bg-surface-white p-3 rounded-lg shadow-2xl">
          <div class="flex items-center gap-2.5">
            <div>
              <div class="font-medium text-base text-ink-gray-8">
                {{ $user(user).full_name }}
              </div>
            </div>
          </div>
          <div class="mt-0.5 text-p-sm text-ink-gray-6">{{ $user(user).bio }}</div>
          <div class="text-p-xs text-ink-gray-6 mt-2">
            {{ $user(user).discussions_count_3m }}
            {{ pluralize($user(user).discussions_count_3m, 'post', 'posts') }},
            {{ $user(user).comments_count_3m }}
            {{ pluralize($user(user).comments_count_3m, 'reply', 'replies') }} in the last 3 months
          </div>
        </div>
      </HoverCardContent>
    </HoverCardPortal>
  </HoverCardRoot>
</template>

<script setup lang="ts">
import UserAvatar from './UserAvatar.vue'
import {
  HoverCardRoot,
  HoverCardPortal,
  HoverCardTrigger,
  HoverCardContent,
  HoverCardArrow,
} from 'reka-ui'
import { ref } from 'vue'

defineOptions({
  inheritAttrs: false,
})

defineProps({
  user: {
    type: String,
    required: true,
  },
})

function pluralize(count: number, singular: string, plural: string) {
  return count === 1 ? singular : plural
}

const userCardOpen = ref(false)
</script>
