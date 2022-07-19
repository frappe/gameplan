<template>
  <header class="flex items-center justify-between w-full h-14">
    <div
      class="flex-shrink-0 w-64 px-4 font-bold tracking-widest text-gray-700 uppercase"
    >
      Gameplan
    </div>
    <div class="w-full pl-16 pr-10" v-if="false">
      <div class="relative w-full">
        <div
          class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none"
        >
          <FeatherIcon name="search" class="w-4 h-4 text-gray-500" />
        </div>
        <input
          id="search"
          name="search"
          class="block w-full py-1 pl-10 pr-3 text-sm placeholder-gray-500 bg-gray-100 border border-transparent rounded-md focus:outline-none focus:ring-0 focus:border-gray-100 focus:shadow focus:text-gray-900 focus:placeholder-gray-400 focus:bg-white"
          placeholder="Search"
          type="search"
        />
      </div>
    </div>
    <div>
      <UserDropdown />
    </div>
  </header>
</template>
<script>
import UserDropdown from './UserDropdown.vue'
export default {
  name: 'AppNavbar',
  components: { UserDropdown },
}
</script>
