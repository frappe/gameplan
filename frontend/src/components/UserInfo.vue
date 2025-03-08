<template>
  <slot v-bind="{ user }"></slot>
</template>
<script>
import { useUser } from '@/data/users'

export default {
  name: 'UserInfo',
  props: ['email'],
  computed: {
    user() {
      return useUser(this.email)
    },
  },
}
</script>
