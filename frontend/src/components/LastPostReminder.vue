<template>
  <div v-if="shouldShowReminder">
    <div class="border flex rounded-md p-3 border-outline-gray-2 dark:bg-gray-900">
      <div class="flex-1">
        <div class="flex items-center">
          <span class="lucide-alert-triangle size-4 shrink-0 mr-2.5 text-ink-gray-8" />
          <h2 class="text-p-base-medium text-ink-gray-8">You haven't posted in a while</h2>
        </div>
        <div class="ml-6.5">
          <p class="text-ink-gray-6 text-p-base">
            It's been {{ daysSinceLastPost }} days since your last post. Share your thoughts or
            updates to keep the conversation going.
          </p>
        </div>
      </div>
      <div class="ml-auto">
        <Button icon="lucide-x" variant="ghost" @click="dismiss" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useCall } from 'frappe-ui'
import { dayjs } from 'frappe-ui'
import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
let lastPostAt = useCall<string>({
  url: `/api/v2/method/GP User Profile/get_last_post`,
  cacheKey: 'last_post_at',
  staleOnError: true,
})

const daysSinceLastPost = computed(() => {
  if (!lastPostAt.data) return 0
  return dayjs().diff(dayjs(lastPostAt.data), 'days')
})

let lastDismissedAt = useLocalStorage<string>('last_post_reminder_dismissed', '')

const shouldShowReminder = computed(() => {
  if (daysSinceLastPost.value <= 7) return false
  if (!lastDismissedAt.value) return true

  const hoursSinceDismissed = dayjs().diff(dayjs(lastDismissedAt.value), 'hours')
  return hoursSinceDismissed >= 24
})

function dismiss() {
  lastDismissedAt.value = dayjs().toISOString()
}
</script>
