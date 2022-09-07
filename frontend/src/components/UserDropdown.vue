<template>
  <Dropdown
    placement="right"
    :options="[
      {
        label: 'My Profile',
        route: {
          name: 'PersonProfile',
          params: { personId: $user().user_profile },
        },
      },
      {
        label: 'Log out',
        handler: () => logout(),
      },
    ]"
  >
    <template v-slot="{ open }">
      <button
        class="flex w-full items-center space-x-2 rounded-md p-2 text-left text-base font-medium"
        :class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
      >
        <Avatar
          :label="$user().full_name"
          :imageURL="$user().user_image"
          size="sm"
        />
        <span class="hidden sm:inline">{{ $user().full_name }}</span>
        <FeatherIcon name="chevron-down" class="hidden h-4 w-4 sm:inline" />
      </button>
    </template>
  </Dropdown>
</template>
<script>
import { FeatherIcon, Dropdown, Avatar, Link } from 'frappe-ui'

export default {
  name: 'UserDropdown',
  components: {
    Dropdown,
    FeatherIcon,
    Avatar,
    Link,
  },
  methods: {
    logout() {
      this.$call('logout').then(() => (window.location.href = '/login'))
    },
  },
}
</script>
