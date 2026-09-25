<template>
  <!-- One width for both states: min-w-16 holds the button steady as the label
       swaps between Join and Leave, so the row never shifts. -->
  <Button
    :size="size"
    variant="subtle"
    :loading="isJoining"
    :label="isJoined ? `Leave ${community.title}` : `Join ${community.title}`"
    class="min-w-16 shrink-0"
    @click="toggleMembership"
  >
    {{ isJoined ? 'Leave' : 'Join' }}
  </Button>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, toast } from 'frappe-ui'
import { confirmLeaveCommunity, isCommunityJoined, joinCommunity } from '@/data/communities'
import type { Community } from '@/data/communities'

const props = withDefaults(
  defineProps<{
    community: Community
    size?: 'xs' | 'sm' | 'md'
  }>(),
  { size: 'sm' },
)

// Leaving runs inside the confirm dialog, which owns its own loading state.
const isJoining = ref(false)

const isJoined = computed(() => isCommunityJoined(props.community))

async function toggleMembership() {
  if (isJoined.value) {
    confirmLeaveCommunity(props.community)
    return
  }

  isJoining.value = true
  try {
    await joinCommunity(props.community)
    toast.success(`Joined ${props.community.title}`)
  } catch (error) {
    toast.error(errorMessage(error) || 'Could not join this community')
  } finally {
    isJoining.value = false
  }
}

function errorMessage(error: unknown) {
  if (error && typeof error === 'object' && 'messages' in error) {
    const messages = (error as { messages?: string[] }).messages
    if (messages?.length) return messages[0]
  }
  return error instanceof Error ? error.message : ''
}
</script>
