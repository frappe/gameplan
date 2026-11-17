<template>
  <UserAvatarWithHover v-if="users.length === 1" size="2xl" :user="users[0]" />
  <!-- Two avatars overlapping side by side in the 40px slot a single avatar uses, the newest
       in front on the left. Its padded wrapper paints the row's surface as a gap between them. -->
  <div v-else class="flex size-10 shrink-0 items-center">
    <span
      class="relative z-[1] flex rounded-full bg-surface-base p-0.5 sm:group-hover:bg-surface-gray-1"
    >
      <UserAvatarWithHover size="md" :user="users[0]" />
    </span>
    <span class="-ml-3 flex">
      <UserAvatarWithHover size="md" :user="users[1]" />
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
