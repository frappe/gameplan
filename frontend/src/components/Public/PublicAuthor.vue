<template>
  <div class="flex min-w-0 items-center gap-2">
    <UserAvatar :user="user" :size="size" />
    <span class="truncate text-base-medium text-ink-gray-8">{{ $user(user).full_name }}</span>
    <span v-if="timestamp" class="shrink-0 text-sm text-ink-gray-5" :title="timestamp">
      {{ relativeTimestamp(timestamp) }}
    </span>
  </div>
</template>

<script setup lang="ts">
import UserAvatar from '@/components/UserAvatar.vue'
import { relativeTimestamp } from '@/utils'

// `user` is a profile handle here, never an email: that is all the server sends someone
// who is not signed in. The users store looks the handle up for a name and an avatar.
withDefaults(defineProps<{ user: string; timestamp?: string | null; size?: string }>(), {
  timestamp: null,
  size: 'md',
})
</script>
