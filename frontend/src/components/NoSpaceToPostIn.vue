<template>
  <EmptyStateBox>
    <span class="lucide-layers h-7 w-7 text-ink-gray-4" />
    <span class="mt-2">No space to post in</span>
    <span class="mt-1 text-p-sm text-ink-gray-5">{{ hint }}</span>
  </EmptyStateBox>
</template>

<script setup lang="ts">
// Shown wherever a discussion has to pick a space and `canPostInSpace` leaves nothing to
// pick: the space dialog and the composer itself. Shared so the two cannot drift into
// telling the same user two different things.
import { computed } from 'vue'
import EmptyStateBox from './EmptyStateBox.vue'
import { useSessionUser } from '@/data/users'
import { isGuest } from '@/utils/permissions'

const sessionUser = useSessionUser()

// A guest can never start a discussion, in any space, so telling them to join one is
// advice they cannot act on. Say what is actually true for them instead.
const hint = computed(() =>
  isGuest(sessionUser)
    ? 'Guests can reply to discussions, but not start them.'
    : 'Join a space, or ask an admin to add you to one.',
)
</script>
