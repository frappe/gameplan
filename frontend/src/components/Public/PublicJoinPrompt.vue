<template>
  <div>
    <div class="rounded-lg border border-outline-gray-2 px-5 py-4">
      <div class="text-base-semibold text-ink-gray-8">{{ title }}</div>
      <p class="mt-1 text-p-base text-ink-gray-6">
        {{
          signupEnabled()
            ? 'Log in or create an account to reply, react and follow along.'
            : 'Log in to reply, react and follow along.'
        }}
      </p>
      <PublicLoginButtons class="mt-3" size="md" />
    </div>
    <!-- Under the prompt rather than in the layout, so it never shows before the page has loaded. -->
    <p class="mt-6 text-p-sm text-ink-gray-5">
      This page is public. Videos and documents embedded in posts (from YouTube, Vimeo, Figma,
      Google Docs and similar) load from those sites, so they can see that you visited.
    </p>
  </div>
</template>

<script setup lang="ts">
import { signupEnabled } from '@/utils/publicAccess'
import PublicLoginButtons from './PublicLoginButtons.vue'

withDefaults(defineProps<{ title?: string }>(), { title: 'Join the conversation' })
</script>
