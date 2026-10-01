<template>
  <div class="rounded-lg border border-outline-gray-2 px-4 py-3">
    <div class="flex items-center justify-between gap-2">
      <div class="text-base-semibold text-ink-gray-8">{{ poll.title }}</div>
      <span class="shrink-0 text-sm text-ink-gray-5">
        {{ poll.stopped_at ? 'Closed' : 'Open' }} ·
        {{ poll.total_votes === 1 ? '1 vote' : `${poll.total_votes || 0} votes` }}
      </span>
    </div>
    <div class="mt-3 space-y-2">
      <div v-for="option in options" :key="option.name">
        <div class="flex justify-between text-p-sm text-ink-gray-7">
          <span>{{ option.title }}</span>
          <span>{{ Math.round(option.percentage || 0) }}%</span>
        </div>
        <div class="mt-1 h-1.5 rounded-full bg-surface-gray-2">
          <div
            class="h-1.5 rounded-full bg-surface-gray-6"
            :style="{ width: `${Math.round(option.percentage || 0)}%` }"
          />
        </div>
      </div>
    </div>
    <div class="mt-3 flex items-center justify-between gap-2">
      <PublicReactions :reactions="poll.reactions" />
      <Button v-if="!poll.stopped_at" size="sm" label="Log in to vote" @click="goToLogin" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import { loginUrl } from '@/utils/publicAccess'
import PublicReactions from './PublicReactions.vue'

// Results only: the server sends each option's share of the votes and never who voted.
export interface PublicPollRow {
  name: string
  title: string
  owner: string | null
  creation: string
  stopped_at: string | null
  total_votes: number
  options: { name: string; title: string; idx: number; percentage: number }[]
  reactions: { emoji: string }[]
}

const props = defineProps<{ poll: PublicPollRow }>()
const options = computed(() => [...(props.poll.options || [])].sort((a, b) => a.idx - b.idx))

function goToLogin() {
  window.location.href = loginUrl()
}
</script>
