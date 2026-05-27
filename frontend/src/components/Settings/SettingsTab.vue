<template>
  <div class="flex min-h-0 flex-col">
    <h2 class="text-xl font-semibold text-ink-gray-9">Settings</h2>

    <div class="mt-6 divide-y overflow-y-auto pb-2">
      <a href="/update-password">
        <Button variant="solid">
          Update Password
        </Button>
      </a>
    </div>
    <hr class="my-4 border-0 border-t border-outline-gray-4" />

    <div class="mt-2">
      <h3 class="text-lg font-semibold text-ink-gray-9">Notifications</h3>

      <div class="mt-3 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-medium text-ink-gray-8">Inactivity digest</p>
          <p class="mt-1 text-sm text-ink-gray-5">
            Email me a catch-up summary when I have been inactive for 7 days.
          </p>
        </div>

        <Switch
          class="shrink-0"
          size="sm"
          v-model="weeklyDigest"
          :disabled="updateWeeklyDigest.loading"
          @update:model-value="saveWeeklyDigest"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Switch, useCall } from 'frappe-ui'
import { useSessionUser } from '@/data/users'

const sessionUser = useSessionUser()
const weeklyDigest = ref(false)
const savedWeeklyDigest = ref(false)
let previousWeeklyDigest = false

const updateWeeklyDigest = useCall<boolean, { weekly_digest: boolean }>({
  url: '/api/v2/method/gameplan.api.update_weekly_digest',
  method: 'POST',
  immediate: false,
  onSuccess(value) {
    sessionUser.weekly_digest = Boolean(value)
    savedWeeklyDigest.value = Boolean(value)
  },
  onError() {
    weeklyDigest.value = previousWeeklyDigest
  },
})

watch(
  () => sessionUser.weekly_digest,
  (value) => {
    savedWeeklyDigest.value = Boolean(value)
    weeklyDigest.value = savedWeeklyDigest.value
  },
  { immediate: true },
)

function saveWeeklyDigest(value: boolean) {
  previousWeeklyDigest = savedWeeklyDigest.value
  updateWeeklyDigest.submit({ weekly_digest: value })
}
</script>
