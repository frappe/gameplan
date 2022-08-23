<template>
  <header class="flex items-center justify-between w-full h-14">
    <router-link
      class="flex-shrink-0 font-bold tracking-widest text-gray-700 uppercase sm:px-4 sm:w-64"
      :to="{ name: 'Home' }"
    >
      Gameplan
    </router-link>
    <div class="hidden w-full sm:pr-10 sm:pl-16 sm:block">
      <AppSearch />
    </div>
    <div class="flex items-center space-x-2 shrink-0">
      <MobileNav />
      <UserDropdown />
    </div>
  </header>
</template>
<script>
import UserDropdown from './UserDropdown.vue'
import AppSearch from './AppSearch.vue'
import MobileNav from './MobileNav.vue';
export default {
  name: 'AppNavbar',
  components: { UserDropdown, AppSearch, MobileNav },
}
</script>
