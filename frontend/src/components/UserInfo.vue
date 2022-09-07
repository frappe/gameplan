<template>
  <slot v-bind="{ user }"></slot>
</template>
<script>
import { userInfo } from '@/data/users'

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
