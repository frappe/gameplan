<template>
  <Avatar
    v-if="user"
    :label="userInfo.full_name"
    :image="userInfo.user_image"
    :style="{
      backgroundColor: userInfo.image_background_color || null,
      filter: userInfo.isDisabled ? 'grayscale(1)' : null,
    }"
    :title="userInfo.isDisabled ? 'User is disabled' : null"
    v-bind="$attrs"
  />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'
import { useUser } from '@/data/users'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  user: {
    type: String,
    required: true,
  },
})

const userInfo = computed(() => useUser(props.user))
</script>
