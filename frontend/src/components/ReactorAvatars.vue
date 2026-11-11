<template>
  <UserAvatarWithHover v-if="users.length === 1" size="2xl" :user="users[0]" />
  <!-- Two avatars stacked in the 40px slot a single avatar uses, the newest in front.
       The padded wrapper paints the row's surface as a gap between them. -->
  <div v-else class="relative size-10 shrink-0">
    <span class="absolute left-0 top-0 flex">
      <UserAvatarWithHover size="lg" :user="users[1]" />
    </span>
    <span
      class="absolute -bottom-0.5 -right-0.5 flex rounded-full bg-surface-base p-0.5 sm:group-hover:bg-surface-gray-1"
    >
      <UserAvatarWithHover size="lg" :user="users[0]" />
    </span>
  </div>
</template>

<script setup lang="ts">
import UserAvatarWithHover from './UserAvatarWithHover.vue'

defineProps<{
  /** Newest first. Needs at least one. */
  users: string[]
}>()
</script>
