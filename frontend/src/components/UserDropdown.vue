<template>
  <Dropdown
    placement="right"
    :options="[
      {
        label: 'My Profile',
        route: { name: 'People', params: { person: 'profile' } },
      },
      { label: 'Settings', route: { name: 'Settings' } },
    ]"
  >
    <template v-slot="{ open }">
      <button
        class="flex items-center w-full p-2 space-x-2 text-base font-medium text-left rounded-md"
        :class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
      >
        <Avatar
          :label="$user().full_name"
          :imageURL="$user().user_image"
          size="sm"
        />
        <span class="hidden sm:inline">{{ $user().full_name }}</span>
        <FeatherIcon name="chevron-down" class="hidden w-4 h-4 sm:inline" />
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
}
</script>
