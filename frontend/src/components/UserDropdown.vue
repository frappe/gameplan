<template>
  <Dropdown :options="dropdownItems">
    <template v-slot="{ open }">
      <slot name="trigger" :open="open"></slot>
    </template>
  </Dropdown>

  <Dialog v-if="loadDevUserList" v-model:open="devUserDialogOpen" title="Switch user" size="sm">
    <!-- Capped so the list scrolls on its own and the filter and the error panel
         stay in view. The negative margin lines the filter up with the title. -->
    <component :is="DevUserList" class="-mx-3 max-h-[60vh]" @close="devUserDialogOpen = false" />
  </Dialog>
</template>
<script setup>
import { h, computed, ref, shallowRef } from 'vue'
import { Dialog, Dropdown } from 'frappe-ui'
import { settingsShortcutLabel, showSettingsDialog } from '@/components/Settings'
import { useUser } from '@/data/users'
import { session } from '@/data/session'
import { useTheme } from '@/utils/useTheme'
import { isAnonymousVisitor, loginUrl, signupEnabled, signupUrl } from '@/utils/publicAccess'

const user = useUser()
const { currentTheme, setTheme } = useTheme()
// `import.meta.env.DEV` is a compile-time constant, so a production build folds
// this to null and drops the dynamic import. The list is never bundled.
const loadDevUserList = import.meta.env.DEV ? () => import('@/components/DevUserList.vue') : null
const DevUserList = shallowRef(null)
const devUserDialogOpen = ref(false)

const dropdownItems = computed(() => [
  {
    icon: 'lucide-user',
    label: 'My Profile',
    condition: () => !isAnonymousVisitor(),
    route: {
      name: 'PersonProfileProfile',
      params: { personId: user.user_profile },
    },
  },
  {
    icon: 'lucide-bookmark',
    label: 'Bookmarks',
    condition: () => !isAnonymousVisitor(),
    route: { name: 'Bookmarks' },
  },
  {
    icon: 'lucide-list-todo',
    label: 'Tasks',
    condition: () => !isAnonymousVisitor(),
    route: { name: 'MyTasks' },
  },
  {
    icon: 'lucide-files',
    label: 'Pages',
    condition: () => !isAnonymousVisitor(),
    route: { name: 'MyPages' },
  },
  {
    icon: 'lucide-settings',
    label: 'Settings',
    condition: () => !isAnonymousVisitor(),
    onClick: () => showSettingsDialog(),
    slots: {
      suffix: () => h('span', { class: 'text-xs text-ink-gray-4' }, settingsShortcutLabel),
    },
  },
  {
    icon: 'lucide-moon',
    label: 'Toggle theme',
    submenu: [
      {
        label: 'Light Mode',
        icon: 'lucide-sun',
        slots: {
          suffix: () => themeCheckmark('light'),
        },
        onClick: () => setTheme('light'),
      },
      {
        label: 'Dark Mode',
        icon: 'lucide-moon',
        slots: {
          suffix: () => themeCheckmark('dark'),
        },
        onClick: () => setTheme('dark'),
      },
      {
        label: 'System Default',
        icon: 'lucide-monitor',
        slots: {
          suffix: () => themeCheckmark('system'),
        },
        onClick: () => setTheme('system'),
      },
    ],
  },
  {
    icon: () => h('span', { class: 'lucide-credit-card' }),
    label: 'Subscription',
    condition: () =>
      !isAnonymousVisitor() && user.isNotGuest && window.frappecloud_host && window.site_name,
    onClick: () => {
      window.open(`${window.frappecloud_host}/dashboard/subscription/${window.site_name}`, '_blank')
    },
  },
  {
    icon: 'lucide-arrow-left-right',
    label: 'Switch user',
    condition: () => !isAnonymousVisitor() && Boolean(loadDevUserList),
    onClick: openDevUserDialog,
  },
  {
    icon: 'lucide-log-out',
    label: 'Log out',
    condition: () => !isAnonymousVisitor(),
    onClick: () => session.logout.submit(),
  },
  {
    icon: 'lucide-user-plus',
    label: 'Sign up',
    condition: () => isAnonymousVisitor() && signupEnabled(),
    onClick: () => {
      window.location.href = signupUrl()
    },
  },
  {
    icon: 'lucide-log-in',
    label: 'Log in',
    condition: isAnonymousVisitor,
    onClick: () => {
      window.location.href = loginUrl()
    },
  },
])

// Load the list before the dialog opens, not as an async component inside it.
// That renders a frame late: the empty dialog grows, and the filter misses the
// dialog's autofocus pass.
async function openDevUserDialog() {
  DevUserList.value ??= (await loadDevUserList()).default
  devUserDialogOpen.value = true
}

function themeCheckmark(theme) {
  if (currentTheme.value !== theme) return null
  return h('span', { class: 'lucide-check size-4 text-ink-gray-6' })
}
</script>
