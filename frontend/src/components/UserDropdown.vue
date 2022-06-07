<template>
  <Menu as="div" class="relative w-full" v-slot="{ open }">
    <MenuButton
      class="flex items-center w-full px-2 py-2 space-x-2 text-base font-medium text-left rounded-md"
      :class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
    >
      <Avatar
        :label="$user().full_name"
        :imageURL="$user().user_image"
        size="sm"
      />
      <span>
        {{ $user().full_name }}
      </span>
      <FeatherIcon name="chevron-down" class="w-4 h-4" />
    </MenuButton>
    <transition
      enter-active-class="transition"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
    >
      <MenuItems
        class="absolute left-0 w-full mt-0.5 rounded-md bg-white shadow-lg p-1"
      >
        <MenuItem v-slot="{ active }">
          <router-link
            :to="{ name: 'People', params: { person: 'profile' } }"
            :class="[
              active ? 'bg-gray-100' : '',
              'flex rounded-md text-gray-900 items-center w-full px-2 py-2 text-sm',
            ]"
          >
            My Profile
          </router-link>
        </MenuItem>
        <MenuItem v-slot="{ active }">
          <router-link
            to="/settings"
            :class="[
              active ? 'bg-gray-100' : '',
              'flex rounded-md text-gray-900 items-center w-full px-2 py-2 text-sm',
            ]"
          >
            Settings
          </router-link>
        </MenuItem>
      </MenuItems>
    </transition>
  </Menu>
</template>
<script>
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'
import FeatherIcon from 'frappe-ui/src/components/FeatherIcon.vue'
import Avatar from 'frappe-ui/src/components/Avatar.vue'
import Link from 'frappe-ui/src/components/Link.vue'
export default {
  name: 'UserDropdown',
  components: {
    Menu,
    MenuButton,
    MenuItems,
    MenuItem,
    FeatherIcon,
    Avatar,
    Link,
  },
}
</script>
