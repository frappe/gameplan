<template>
  <div class="flex h-screen flex-col items-center bg-surface-base px-4 pt-[20vh]">
    <GameplanLogo class="mb-8 size-10 rounded-[10px]" />
    <EmptyStateBox
      class="w-full max-w-md"
      icon="lucide-link-2-off"
      title="This invitation link is no longer valid"
      :description="description"
    >
      <Button
        v-if="session.isLoggedIn"
        class="mt-4"
        variant="subtle"
        label="Go to Home"
        route="/"
      />
      <Button v-else class="mt-4" variant="subtle" label="Sign in" href="/login?redirect-to=/g" />
    </EmptyStateBox>
  </div>
</template>

<script setup lang="ts">
// Where gameplan.api.accept_invitation sends a dead invitation link. A public route:
// the person who opens it is usually not signed in, so it renders without the app shell.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Button, usePageMeta } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import GameplanLogo from '@/components/GameplanLogo.vue'
import { session } from '@/data/session'

const route = useRoute()

const description = computed(() => {
  if (route.query.reason !== 'accepted') return 'Ask the person who invited you to send a new one.'
  return session.isLoggedIn
    ? 'It has already been accepted.'
    : 'It has already been accepted. Sign in to continue.'
})

usePageMeta(() => ({ title: 'Invitation link not valid' }))
</script>
