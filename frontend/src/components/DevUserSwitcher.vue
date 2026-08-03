<template>
  <PopoverRoot v-model:open="isOpen">
    <!-- Bottom left, but clear of the two things that already live there: the
         mobile tab bar below `sm`, and the desktop rail from `sm` up. -->
    <PopoverTrigger as-child>
      <button
        type="button"
        class="fixed bottom-20 left-3 z-[200] flex items-center gap-2 rounded-full border border-outline-gray-2 bg-surface-elevation-2 py-1 pl-1 pr-2.5 shadow-lg transition-opacity hover:opacity-100 sm:bottom-3 sm:left-16"
        :class="isOpen ? 'opacity-100' : 'opacity-60'"
        title="Dev only — switch user"
      >
        <UserAvatar :user="sessionUser.name" size="sm" />
        <span class="max-w-32 truncate text-p-sm text-ink-gray-7">
          {{ sessionUser.full_name }}
        </span>
        <span class="lucide-chevrons-up-down size-3.5 shrink-0 text-ink-gray-5" />
      </button>
    </PopoverTrigger>

    <PopoverPortal>
      <PopoverContent
        side="top"
        align="start"
        :side-offset="8"
        :collision-padding="12"
        class="z-[200] outline-none"
        @open-auto-focus.prevent
      >
        <div
          class="flex max-h-[70vh] w-80 max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-lg bg-surface-elevation-2 shadow-2xl ring-1 ring-outline-gray-2"
          style="transform-origin: var(--reka-popover-content-transform-origin)"
        >
          <div class="flex items-center justify-between gap-2 px-3 pt-3">
            <span class="text-p-sm font-medium text-ink-gray-8">Switch user</span>
            <span class="text-p-xs uppercase tracking-wide text-ink-gray-4">dev only</span>
          </div>

          <div v-if="switchableUsers.length > 6" class="px-3 pt-2">
            <TextInput v-model="query" size="sm" placeholder="Filter" autofocus />
          </div>

          <div class="mt-2 min-h-0 flex-1 overflow-y-auto px-2 pb-2">
            <button
              v-for="user in filteredUsers"
              :key="user.name"
              type="button"
              class="flex w-full items-center gap-2.5 rounded px-2 py-1.5 text-left hover:bg-surface-gray-2 disabled:opacity-60"
              :disabled="Boolean(switchingTo)"
              @click="switchTo(user.name)"
            >
              <UserAvatar :user="user.name" size="md" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-p-sm text-ink-gray-8">{{ user.full_name }}</span>
                <span class="block truncate text-p-xs text-ink-gray-5">
                  {{ user.name }} · {{ shortRole(user) }}
                </span>
              </span>
              <LoadingIndicator v-if="switchingTo === user.name" class="size-4 text-ink-gray-5" />
              <span
                v-else-if="user.name === sessionUser.name"
                class="lucide-check size-4 shrink-0 text-ink-gray-7"
              />
            </button>

            <p v-if="!filteredUsers.length" class="px-2 py-3 text-p-sm text-ink-gray-5">
              No user matches "{{ query }}".
            </p>
          </div>

          <!-- Signing in needs a password, and every seeded user on a local site
               shares one. It is only revealed once it turns out to be wrong, so
               the common case stays a single click. -->
          <div v-if="showPassword" class="space-y-1.5 border-t border-outline-gray-2 p-3">
            <FormLabel label="Password" size="sm" />
            <TextInput v-model="password" size="sm" type="password" @keydown.enter="retry" />
            <p v-if="error" class="text-p-xs text-ink-gray-5">{{ error }}</p>
          </div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<script setup lang="ts">
/**
 * A floating "log in as somebody else" control, mounted only by a dev build.
 *
 * It signs in for real rather than impersonating: frappe's `impersonate` needs
 * the System Manager role, so the first switch to an ordinary member would be
 * one-way. A plain login works from any user, and costs no backend surface —
 * an endpoint that hands out sessions is not something to add for convenience.
 */
import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { FormLabel, LoadingIndicator, TextInput, useCall } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import { activeUsers, useSessionUser, type UserInfo } from '@/data/users'

defineOptions({ name: 'DevUserSwitcher' })

const sessionUser = useSessionUser()

const isOpen = ref(false)
const query = ref('')
const switchingTo = ref('')
const failedUser = ref('')
const error = ref('')
const showPassword = ref(false)
// Every seeded user on a local bench shares `admin`. Kept per browser so a site
// with a different one is typed in once.
const password = useLocalStorage('gameplan:dev-switcher-password', 'admin')

// v1 on purpose, against the house rule: `login` is a `cmd`, not a dotted path,
// so /api/v2/method/login answers 200 with `{}` and leaves the session alone.
const login = useCall<{ full_name: string }, { usr: string; pwd: string }>({
  url: '/api/method/login',
  method: 'POST',
  immediate: false,
})

const switchableUsers = computed(() => activeUsers.value)

const filteredUsers = computed(() => {
  const search = query.value.trim().toLowerCase()
  if (!search) return switchableUsers.value
  return switchableUsers.value.filter((user) => {
    return `${user.full_name} ${user.name}`.toLowerCase().includes(search)
  })
})

function shortRole(user: UserInfo) {
  return user.role?.replace('Gameplan ', '') || 'User'
}

async function switchTo(email: string) {
  if (switchingTo.value) return
  if (email === sessionUser.name) {
    isOpen.value = false
    return
  }

  switchingTo.value = email
  error.value = ''
  try {
    await login.submit({ usr: email, pwd: password.value })
    // Ask the cookie, not the call. `useCall` resolves rather than rejects on an
    // HTTP error, and a v1 response puts its payload at the top level instead of
    // under `data`, so neither a thrown error nor the return value says whether
    // this worked. Frappe rewrites `user_id` only once the session really moved.
    if (sessionUserFromCookie() === email) {
      // A hard reload, not a route push: the session user is baked into the boot
      // payload, the socket rooms and every cached resource, and none of that is
      // built to be swapped underneath a running app.
      window.location.reload()
      return
    }
    fail(email, login.error?.message)
  } catch (e) {
    fail(email, e instanceof Error ? e.message : undefined)
  }
}

function fail(email: string, message?: string) {
  failedUser.value = email
  // Frappe answers a wrong password with a bare "UNAUTHORIZED", which says
  // nothing about the one field there is to change. Anything that reads like a
  // real sentence is worth showing; a lone status word is not.
  const isBareStatus = !message || !message.includes(' ')
  error.value = isBareStatus ? `Wrong password for ${email}. Press enter to retry.` : message
  showPassword.value = true
  switchingTo.value = ''
}

function sessionUserFromCookie() {
  return new URLSearchParams(document.cookie.split('; ').join('&')).get('user_id')
}

function retry() {
  if (failedUser.value) switchTo(failedUser.value)
}
</script>
