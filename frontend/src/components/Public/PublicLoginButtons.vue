<template>
  <div class="flex shrink-0 items-center gap-2">
    <Button
      v-if="route.name !== 'Search'"
      :size="size"
      variant="ghost"
      icon="lucide-search"
      label="Search"
      :route="{ name: 'Search' }"
    />
    <Button :size="size" variant="subtle" label="Log in" :link="loginUrl()" target="_self" />
    <Button
      v-if="signupEnabled()"
      :size="size"
      variant="solid"
      label="Sign up"
      :link="signupUrl()"
      target="_self"
    />
  </div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import { useRoute } from 'vue-router'
import { loginUrl, signupEnabled, signupUrl } from '@/utils/publicAccess'

withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' })
const route = useRoute()
</script>
