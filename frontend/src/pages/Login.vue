<template>
  <div class="flex h-screen w-screen justify-center bg-surface-gray-2">
    <div class="mt-32 w-full px-4">
      <GameplanLogo class="mx-auto h-8 w-8" />
      <div class="mt-6 flex items-center justify-center space-x-1.5">
        <span class="text-3xl font-semibold text-ink-gray-8">Login to</span>
        <GameplanLogoType class="h-6 text-ink-gray-8" />
      </div>
      <div class="mx-auto mt-6 w-full px-4 sm:w-96">
        <form v-if="showEmailLogin" @submit.prevent="submit">
          <div>
            <FormControl
              variant="outline"
              size="md"
              :type="(email || '').toLowerCase() === 'administrator' ? 'text' : 'email'"
              label="Email"
              v-model="email"
              placeholder="jane@example.com"
              :disabled="session.login.loading"
            />
          </div>
          <div class="mt-4">
            <FormControl
              variant="outline"
              size="md"
              label="Password"
              v-model="password"
              placeholder="••••••"
              :disabled="session.login.loading"
              type="password"
            />
          </div>
          <ErrorMessage class="mt-2" :message="session.login.error" />
          <Button variant="solid" class="mt-6 w-full" :loading="session.login.loading">
            Login
          </Button>
          <button
            v-if="authProviders.data?.length"
            class="mt-2 w-full py-2 text-base text-ink-gray-5"
            @click="showEmailLogin = false"
          >
            Login using other methods
          </button>
        </form>
        <div class="mx-auto space-y-2" v-if="authProviders.data && !showEmailLogin">
          <Button @click="showEmailLogin = true" variant="solid" class="w-full">
            Login via email
          </Button>
          <a
            class="block w-full rounded border bg-surface-gray-7 px-3 py-1 text-center text-base h-7 focus:outline-none focus:ring-2 focus:ring-outline-gray-3 text-ink-white transition-colors hover:bg-surface-gray-5"
            v-for="provider in authProviders.data"
            :key="provider.name"
            :href="provider.auth_url"
          >
            Login via {{ provider.provider_name }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { FormControl } from 'frappe-ui'
import { useCall } from 'frappe-ui/src/data-fetching'
import { session } from '@/data/session'
import GameplanLogo from '@/components/GameplanLogo.vue'
import GameplanLogoType from '@/components/GameplanLogoType.vue'

let showEmailLogin = ref(false)
let email = ref('')
let password = ref('')

interface OAuthProviders {
  name: string
  provider_name: string
  auth_url: string
  icon: string
}

let authProviders = useCall<OAuthProviders[]>({
  url: '/api/v2/method/gameplan.api.oauth_providers',
  immediate: true,
  onSuccess(data) {
    showEmailLogin.value = data.length === 0
  },
})

function submit() {
  session.login.submit({
    usr: email,
    pwd: password,
  })
}
</script>
