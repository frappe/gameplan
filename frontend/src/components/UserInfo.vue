<template>
  <slot v-bind="{ user: $resources.user.data || fallback }"></slot>
</template>
<script>
export default {
  name: 'UserInfo',
  props: ['email'],
  resources: {
    user() {
      return {
        method: 'teams.api.get_user_info',
        cache: ['user_info', this.email],
        params: {
          email: this.email,
        },
        auto: true,
        initialData: this.fallback,
      }
    },
  },
  computed: {
    fallback() {
      return {
        email: this.email,
        full_name: this.email.split('@')[0],
        user_image: null,
      }
    },
  },
}
</script>
