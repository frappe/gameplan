<template>
  <slot v-bind="{ user }"></slot>
</template>
<script>
import { userInfo } from '@/resources/users'

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
