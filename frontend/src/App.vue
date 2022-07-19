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
</template>

<script>
import AppLayout from './components/AppLayout.vue'
import AppSidebar from './components/AppSidebar.vue'
import AppNavbar from './components/AppNavbar.vue'

export default {
  components: {
    AppLayout,
    AppSidebar,
    AppNavbar,
  },
}
</script>
