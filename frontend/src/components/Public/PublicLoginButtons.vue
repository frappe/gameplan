<template>
  <div class="flex shrink-0 items-center gap-2">
    <Button :size="size" variant="subtle" label="Log in" @click="go(loginUrl())" />
    <Button
      v-if="signupEnabled()"
      :size="size"
      variant="solid"
      label="Sign up"
      @click="go(signupUrl())"
    />
  </div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import { loginUrl, signupEnabled, signupUrl } from '@/utils/publicAccess'

withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' })

// Frappe's own login and signup pages, which return the visitor to this page.
function go(url: string) {
  window.location.href = url
}
</script>
