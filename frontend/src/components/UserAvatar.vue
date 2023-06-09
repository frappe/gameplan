<template>
  <Avatar
    v-if="user"
    :label="$user(user).full_name"
    :image="$user(user).user_image"
    :style="{
      backgroundColor: $user(user).image_background_color || null,
      filter: $user(user).isDisabled ? 'grayscale(1)' : null,
    }"
    :title="$user(user).isDisabled ? 'User is disabled' : null"
    v-bind="$attrs"
  />
</template>
<script>
import { Avatar } from 'frappe-ui'

export default {
  name: 'UserAvatar',
  inheritAttrs: false,
  components: { Avatar },
  props: ['user'],
}
</script>
