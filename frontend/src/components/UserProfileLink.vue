<template>
  <router-link
    class="inline-flex"
    v-if="canVisitProfile"
    :to="{ name: 'PersonProfileProfile', params: { personId: userProfileName } }"
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
import { isAnonymousVisitor } from '@/utils/publicAccess'

const props = defineProps<{
  user: string | null | undefined
}>()

const userProfileName = computed(() => {
  return useUser(props.user).user_profile || null
})

const canVisitProfile = computed(() => {
  return Boolean(userProfileName.value && !isAnonymousVisitor() && useSessionUser().isNotGuest)
})
</script>
