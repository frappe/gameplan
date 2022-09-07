<template>
  <router-link
    v-if="userProfileName"
    :to="{ name: 'PersonProfile', params: { personId: userProfileName } }"
  >
    <slot />
  </router-link>
  <span v-else>
    <slot />
  </span>
</template>
<script>
export default {
  name: 'UserProfileLink',
  props: ['user'],
  computed: {
    userProfileName() {
      return this.$user(this.user).user_profile || null
    },
  },
}
</script>
