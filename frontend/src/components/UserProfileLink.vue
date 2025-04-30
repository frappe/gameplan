<template>
  <router-link
    class="inline-flex"
    v-if="canVisitProfile"
    :to="{ name: 'PersonProfile', params: { personId: userProfileName } }"
  >
    <slot />
  </router-link>
  <span v-else>
    <slot />
  </span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useSessionUser, useUser } from '@/data/users'

const props = defineProps<{
  user: string | null | undefined
}>()

const userProfileName = computed(() => {
  return useUser(props.user).user_profile || null
})

const canVisitProfile = computed(() => {
  return userProfileName.value && useSessionUser().isNotGuest
})
</script>
