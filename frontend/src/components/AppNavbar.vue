<template>
  <header class="flex items-center justify-between w-full h-14">
    <router-link
      class="flex-shrink-0 w-64 px-4 font-bold tracking-widest text-gray-700 uppercase"
      :to="{ name: 'Home' }"
    >
      Gameplan
    </router-link>
    <div class="w-full pl-16 pr-10">
      <AppSearch />
    </div>
    <div>
      <UserDropdown />
    </div>
  </header>
</template>
<script>
import UserDropdown from './UserDropdown.vue'
import AppSearch from './AppSearch.vue'
export default {
  name: 'AppNavbar',
  components: { UserDropdown, AppSearch },
}
</script>
