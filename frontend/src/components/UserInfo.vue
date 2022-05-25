<template>
  <slot v-bind="{ user }"></slot>
</template>
<script>
import { userInfo } from '@/utils/users.js'

export default {
  name: 'UserInfo',
  props: ['email'],
  computed: {
    user() {
      return userInfo(this.email)
    },
  },
}
</script>
