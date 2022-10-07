<template>
  <router-view v-if="$route.name === 'Onboarding'" />
  <MobileLayout v-else-if="isMobile">
    <router-view />
  </MobileLayout>
  <DesktopLayout v-else>
    <template v-slot:sidebar>
      <AppSidebar />
    </template>
    <template v-slot:main>
      <router-view />
    </template>
  </DesktopLayout>
  <Dialogs />
  <Toasts />
</template>

<script setup>
import { computed } from 'vue'
import DesktopLayout from './components/DesktopLayout.vue'
import AppSidebar from './components/AppSidebar.vue'
import { Dialogs } from '@/utils/dialogs'
import { Toasts } from '@/utils/toasts'
import { useScreenSize } from './utils/composables'
import MobileLayout from './components/MobileLayout.vue'

const size = useScreenSize()
const isMobile = computed(() => size.width < 640)
</script>
