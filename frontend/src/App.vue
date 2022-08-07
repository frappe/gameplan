<template>
  <AppLayout>
    <template v-slot:sidebar>
      <AppSidebar />
    </template>
    <template v-slot:navbar>
      <AppNavbar />
    </template>
    <template v-slot:main>
      <router-view />
    </template>
  </AppLayout>
  <Dialogs />
  <Toasts />
</template>

<script>
import AppLayout from './components/AppLayout.vue'
import AppSidebar from './components/AppSidebar.vue'
import AppNavbar from './components/AppNavbar.vue'
import { Dialogs } from '@/utils/dialogs'
import { Toasts } from '@/utils/toasts'

export default {
  components: {
    AppLayout,
    AppSidebar,
    AppNavbar,
    Dialogs,
    Toasts,
  },
}
</script>
