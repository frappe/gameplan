<template>
  <div class="relative flex h-full flex-col" v-if="$users.data.length">
    <div class="h-full flex-1">
      <div class="flex h-full">
        <div
          class="hidden min-h-0 flex-shrink-0 overflow-hidden hover:overflow-auto sm:block"
        >
          <slot name="sidebar" />
        </div>
        <div class="w-full overflow-auto">
          <div
            class="flex items-center justify-between border-b py-4 px-4 sm:hidden"
          >
            <router-link
              class="flex-shrink-0 font-bold uppercase tracking-widest text-gray-700 sm:w-64 sm:px-4"
              :to="{ name: 'Home' }"
            >
              Gameplan
            </router-link>
            <MobileNav />
          </div>
          <div
            v-if="$readOnlyMode"
            class="right-0 top-0 mb-3 bg-gray-100 px-4 py-3 text-sm text-gray-600"
          >
            <div class="mx-auto max-w-4xl px-4 sm:px-10">
              This site is running in read-only mode. Full functionality will be
              restored soon.
            </div>
          </div>
          <div class="mx-auto max-w-4xl px-4 sm:px-10">
            <slot name="main" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import MobileNav from './MobileNav.vue'

export default {
  name: 'AppLayout',
  components: { MobileNav },
}
</script>
