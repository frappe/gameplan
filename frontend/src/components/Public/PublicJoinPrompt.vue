<template>
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
</template>

<script setup lang="ts">
import { signupEnabled } from '@/utils/publicAccess'
import PublicLoginButtons from './PublicLoginButtons.vue'

withDefaults(defineProps<{ title?: string }>(), { title: 'Join the conversation' })
</script>
