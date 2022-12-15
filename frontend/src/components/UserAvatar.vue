<template>
  <Avatar
    v-if="user"
    :label="$user(user).full_name"
    :imageURL="$user(user).user_image"
    :style="{
      backgroundColor: $user(user).image_background_color || null,
    }"
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
