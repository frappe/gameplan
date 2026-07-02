<template>
  <img
    class="object-cover"
    :src="_user.user_image"
    :alt="`Profile Photo of ${_user.full_name}`"
    :style="{
      backgroundColor: _user.image_background_color || null,
    }"
  />
</template>
<script>
import { useUser } from '@/data/users'

export default {
  name: 'UserImage',
  props: ['user'],
  computed: {
    _user() {
      return useUser(this.user)
    },
  },
}
</script>
