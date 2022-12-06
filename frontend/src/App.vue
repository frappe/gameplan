<template>
  <router-view v-if="['Onboarding', 'Login'].includes($route.name)" />
  <Layout v-else-if="$session.isLoggedIn">
    <router-view />
  </Layout>
  <Dialogs />
  <Toasts />
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { Dialogs } from '@/utils/dialogs'
import { Toasts } from '@/utils/toasts'
import { users } from '@/data/users'
import { useScreenSize } from './utils/composables'

const size = useScreenSize()
const isMobile = computed(() => size.width < 640)
const Layout = computed(() => {
  if (isMobile.value) {
    return defineAsyncComponent(() => import('./components/MobileLayout.vue'))
  } else {
    return defineAsyncComponent(() => import('./components/DesktopLayout.vue'))
  }
})

users.fetch()
</script>
