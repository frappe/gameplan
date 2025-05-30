<template>
  <FrappeUIProvider>
    <ScrollAreaRoot class="h-full overflow-hidden">
      <router-view v-if="['Onboarding', 'Login'].includes($route.name)" />
      <Layout class="hello" v-else-if="$session.isLoggedIn">
        <router-view />
      </Layout>
    </ScrollAreaRoot>
    <NewTaskDialog />
    <Dialogs />
  </FrappeUIProvider>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { FrappeUIProvider } from 'frappe-ui'
import { ScrollAreaRoot } from 'reka-ui'
import { Dialogs } from '@/utils/dialogs'
import { users } from '@/data/users'
import { useScreenSize } from './utils/composables'
import NewTaskDialog from './components/NewTaskDialog/NewTaskDialog.vue'

const screenSize = useScreenSize()
const MobileLayout = defineAsyncComponent(() => import('./components/MobileLayout.vue'))
const DesktopLayout = defineAsyncComponent(() => import('./components/DesktopLayout.vue'))
const Layout = computed(() => {
  if (screenSize.width < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

users.fetch()
</script>
