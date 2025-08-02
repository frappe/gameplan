<template>
  <UserHoverCard :user="user">
    <UserAvatar :user="user" v-bind="$attrs" />
  </UserHoverCard>
</template>

<script setup lang="ts">
import UserAvatar from './UserAvatar.vue'
import UserHoverCard from './UserHoverCard.vue'

defineOptions({
  inheritAttrs: false,
})

defineProps({
  user: {
    type: String,
    required: true,
  },
})
</script>
