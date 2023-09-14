<template>
  <Dropdown :options="dropdownItems">
    <template v-slot="{ open }">
      <button
        class="flex w-[15rem] items-center rounded-md px-2 py-2 text-left"
        :class="open ? 'bg-white shadow-sm' : 'hover:bg-gray-200'"
      >
        <GameplanLogo class="w-8 h-8 rounded" />
        <div class="ml-2 flex flex-col">
          <div class="text-base font-medium text-gray-900 leading-none">
            Gameplan
          </div>
          <div class="mt-1 hidden text-sm text-gray-700 sm:inline leading-none">
            {{ $user().full_name }}
          </div>
        </div>
        <LucideChevronDown class="ml-auto hidden h-4 w-4 sm:inline" />
      </button>
    </template>
  </Dropdown>
</template>
<script>
import { h } from 'vue'
import { Dropdown } from 'frappe-ui'
import { showSettingsDialog } from '@/components/Settings/SettingsDialog.vue'
import LucideCreditCard from '~icons/lucide/credit-card'
import GameplanLogo from './GameplanLogo.vue'

export default {
  name: 'UserDropdown',
  components: {
    Dropdown,
    GameplanLogo,
  },
  computed: {
    dropdownItems() {
      return [
        {
          icon: 'user',
          label: 'My Profile',
          route: {
            name: 'PersonProfile',
            params: { personId: this.$user().user_profile },
          },
        },
        {
          icon: 'settings',
          label: 'Settings & Members',
          onClick: () => showSettingsDialog(),
          condition: () => this.$user().isNotGuest,
        },
        {
          icon: () => h(LucideCreditCard),
          label: 'Subscription',
          condition: () =>
            this.$user().isNotGuest &&
            window.frappecloud_host &&
            window.site_name,
          onClick: () => {
            window.open(
              `${window.frappecloud_host}/dashboard/subscription/${window.site_name}`,
              '_blank',
            )
          },
        },
        {
          icon: 'log-out',
          label: 'Log out',
          onClick: () => this.$session.logout.submit(),
        },
      ]
    },
  },
}
</script>
