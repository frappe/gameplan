<template>
  <router-link
    class="inline-flex"
    v-if="canVisitProfile"
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
    canVisitProfile() {
      return this.userProfileName && this.$user().isNotGuest
    },
  },
}
</script>
