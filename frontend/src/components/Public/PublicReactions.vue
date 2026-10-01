<template>
  <div v-if="totals.length" class="flex flex-wrap gap-1.5">
    <button
      v-for="total in totals"
      :key="total.emoji"
      type="button"
      class="flex items-center gap-1 rounded-full bg-surface-gray-2 px-2 py-0.5 text-sm text-ink-gray-7 hover:bg-surface-gray-3"
      :title="`Log in to react with ${total.emoji}`"
      @click="goToLogin"
    >
      <span>{{ total.emoji }}</span>
      <span>{{ total.count }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { loginUrl } from '@/utils/publicAccess'

// Totals only. The server sends each reaction's emoji and nothing about who reacted.
const props = defineProps<{ reactions?: { emoji: string }[] | null }>()

const totals = computed(() => {
  const counts = new Map<string, number>()
  for (const reaction of props.reactions || []) {
    counts.set(reaction.emoji, (counts.get(reaction.emoji) || 0) + 1)
  }
  return [...counts].map(([emoji, count]) => ({ emoji, count }))
})

function goToLogin() {
  window.location.href = loginUrl()
}
</script>
