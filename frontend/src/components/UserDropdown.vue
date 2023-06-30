<template>
  <Dropdown
    :options="[
      {
        icon: 'user',
        label: 'My Profile',
        route: {
          name: 'PersonProfile',
          params: { personId: $user().user_profile },
        },
      },
      {
        icon: 'settings',
        label: 'Settings & Members',
        onClick: () => showSettingsDialog(),
        condition: () => $user().isNotGuest,
      },
      {
        icon: 'log-out',
        label: 'Log out',
        onClick: () => logout(),
      },
    ]"
  >
    <template v-slot="{ open }">
      <button
        class="flex w-full items-center space-x-2 rounded-md p-2 text-left"
        :class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
      >
        <UserAvatar :user="$user().name" size="md" />
        <span class="hidden text-base font-medium text-gray-900 sm:inline">
          {{ $user().full_name }}
        </span>
        <FeatherIcon name="chevron-down" class="hidden h-4 w-4 sm:inline" />
      </button>
    </template>
  </Dropdown>
</template>
<script>
import { FeatherIcon, Dropdown, Link } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings/SettingsDialog.vue'

export default {
  name: 'UserDropdown',
  components: {
    Dropdown,
    FeatherIcon,
    Link,
  },
  setup() {
    return {
      showSettingsDialog,
    }
  },
  methods: {
    logout() {
      this.$session.logout.submit()
    },
  },
}
</script>
