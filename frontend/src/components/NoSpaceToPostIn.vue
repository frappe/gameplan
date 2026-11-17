<template>
  <EmptyStateBox icon="lucide-layers" title="No space to post in" :description="hint" />
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

// A guest cannot join a space on their own, so telling them to join one is advice they
// cannot act on. They get into a space only when a member invites them.
const hint = computed(() =>
  isGuest(sessionUser)
    ? 'Ask a member to invite you to a space.'
    : 'Join a space, or ask an admin to add you to one.',
)
</script>
