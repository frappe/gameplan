<template>
  <slot v-bind="{ user }"></slot>
</template>
<script>
import { getUser } from '@/data/users'

export default {
  name: 'UserInfo',
  props: ['email'],
  computed: {
    user() {
      return getUser(this.email)
    },
  },
}
</script>
