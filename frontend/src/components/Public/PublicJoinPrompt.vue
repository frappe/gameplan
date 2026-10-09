<template>
  <div>
    <Alert
      :title="title"
      :icon="false"
      :description="
        signupEnabled()
          ? 'Log in or create an account to reply, react and follow along.'
          : 'Log in to reply, react and follow along.'
      "
    >
      <template #actions><PublicLoginButtons size="md" /></template>
    </Alert>
    <!-- Under the prompt rather than in the layout, so it never shows before the page has loaded. -->
    <p class="mt-6 text-p-sm text-ink-gray-5">
      This page is public. Videos and documents embedded in posts (from YouTube, Vimeo, Figma,
      Google Docs and similar) load from those sites, so they can see that you visited.
    </p>
  </div>
</template>

<script setup lang="ts">
import { Alert } from 'frappe-ui'
import { signupEnabled } from '@/utils/publicAccess'
import PublicLoginButtons from './PublicLoginButtons.vue'

withDefaults(defineProps<{ title?: string }>(), { title: 'Join the conversation' })
</script>
