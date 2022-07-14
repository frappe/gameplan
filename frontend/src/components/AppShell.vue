<template>
  <div class="container h-full" v-if="usersResource.data">
    <AppSidebar v-model:sidebarOpen="sidebarOpen" />
    <div class="flex flex-col flex-1 h-full md:pl-64">
      <div
        class="sticky top-0 z-10 pt-1 pl-1 bg-white md:hidden sm:pl-3 sm:pt-3"
      >
        <button
          type="button"
          class="-ml-0.5 -mt-0.5 h-12 w-12 inline-flex items-center justify-center rounded-md text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
          @click="sidebarOpen = true"
        >
          <span class="sr-only">Open sidebar</span>
          <FeatherIcon name="menu" class="w-6 h-6" aria-hidden="true" />
        </button>
      </div>
      <main class="flex-1 h-full">
        <router-view />
      </main>
    </div>
  </div>
  <Dialogs />
  <Toasts />
</template>
<script>
import { ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import { Dialogs } from '@/utils/dialogs'
import { Toasts } from '@/utils/toasts'
import { usersResource } from '@/utils/users'

export default {
  name: 'AppShell',
  components: {
    AppSidebar,
    Dialogs,
    Toasts,
  },
  setup() {
    const sidebarOpen = ref(false)
    return {
      sidebarOpen,
      usersResource,
    }
  },
}
</script>
