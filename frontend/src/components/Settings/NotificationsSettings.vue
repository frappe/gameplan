<template>
  <!-- On phones the dialog's own bar names the tab (Settings/SettingsDialog.vue). -->
  <SettingsHeader class="max-sm:hidden">
    <h2 class="text-lg-semibold text-ink-gray-8">Notifications</h2>
  </SettingsHeader>

  <SettingsBody>
    <div class="space-y-11 pt-6">
      <section>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow title="Enable email digests" description="Send a summary of missed activity">
            <Switch v-model="emailDigestEnabled" />
          </SettingsRow>

          <SettingsRow
            v-if="emailDigestEnabled"
            title="Digest frequency"
            description="Choose how often you receive your digest"
          >
            <Select :options="emailDigestFrequencyOptions" v-model="selectedDigestFrequency" />
          </SettingsRow>

          <SettingsRow
            v-if="emailDigestEnabled"
            title="Send on"
            description="Choose the weekday for your digest"
          >
            <Select :options="emailDigestDayOptions" v-model="selectedDigestDayOfWeek" />
          </SettingsRow>

          <SettingsRow title="Last sent" description="The most recent digest email sent to you">
            <div class="text-base text-ink-gray-6">{{ emailDigestLastSentOn }}</div>
          </SettingsRow>
        </div>
      </section>
    </div>
  </SettingsBody>
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  dayjsLocal,
  Select,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  Switch,
  toast,
  useDoctype,
} from 'frappe-ui'
import { useSessionUser, type EmailDigestDayOfWeek, type EmailDigestFrequency } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'

const sessionUser = useSessionUser()
const userProfiles = useDoctype<GPUserProfile>('GP User Profile')
const DEFAULT_ENABLED_FREQUENCY: EmailDigestFrequency = 'Weekly'
const DIGEST_PREFERENCE_SAVE_DEBOUNCE_MS = 700
const digestPreferenceToastId = 'email-digest-preference-save'

const emailDigestFrequencyOptions: Array<{
  label: EmailDigestFrequency
  value: EmailDigestFrequency
}> = [
  { label: 'Weekly', value: 'Weekly' },
  { label: 'Fortnightly', value: 'Fortnightly' },
  { label: 'Monthly', value: 'Monthly' },
]

const emailDigestDayOptions: Array<{
  label: EmailDigestDayOfWeek
  value: EmailDigestDayOfWeek
}> = [
  { label: 'Monday', value: 'Monday' },
  { label: 'Tuesday', value: 'Tuesday' },
  { label: 'Wednesday', value: 'Wednesday' },
  { label: 'Thursday', value: 'Thursday' },
  { label: 'Friday', value: 'Friday' },
  { label: 'Saturday', value: 'Saturday' },
  { label: 'Sunday', value: 'Sunday' },
]

const emailDigestFrequency = ref<EmailDigestFrequency>(getSessionDigestFrequency())
const emailDigestDayOfWeek = ref<EmailDigestDayOfWeek>(getSessionDigestDayOfWeek())
const savedDigestPreferences = ref<EmailDigestPreferences>(getSessionDigestPreferences())
const isSavingDigestPreference = ref(false)
const shouldSaveAfterCurrentRequest = ref(false)
const digestPreferenceSaveTimeout = ref<number | null>(null)
const pendingDigestPreferenceBaseline = ref<EmailDigestPreferences | null>(null)

const emailDigestEnabled = computed({
  get() {
    return emailDigestFrequency.value !== 'Off'
  },
  set(enabled: boolean) {
    saveDigestFrequency(enabled ? DEFAULT_ENABLED_FREQUENCY : 'Off')
  },
})
// Writable computeds keep the Select's wide `SelectOptionValue | undefined` emit
// from leaking into our narrow handlers — v-model narrows it to the typed union.
const selectedDigestFrequency = computed({
  get: () => emailDigestFrequency.value,
  set: saveDigestFrequency,
})
const selectedDigestDayOfWeek = computed({
  get: () => emailDigestDayOfWeek.value,
  set: saveDigestDayOfWeek,
})
const emailDigestLastSentOn = computed(() => {
  if (!sessionUser.email_digest_last_sent_on) return 'Not sent yet'
  return dayjsLocal(sessionUser.email_digest_last_sent_on).format('D MMM YYYY')
})

watch(
  () => [sessionUser.email_digest_frequency, sessionUser.email_digest_day_of_week] as const,
  () => {
    let nextPreferences = getSessionDigestPreferences()
    let hasLocalChanges = hasUnsavedDigestPreferences()
    savedDigestPreferences.value = nextPreferences
    if (!isSavingDigestPreference.value && !hasLocalChanges) {
      applyLocalDigestPreferences(nextPreferences)
    }
  },
  { immediate: true },
)

onBeforeUnmount(flushPendingDigestPreferenceSave)

function saveDigestFrequency(frequency: EmailDigestFrequency) {
  if (frequency === emailDigestFrequency.value) return
  rememberPendingDigestPreferenceBaseline()
  emailDigestFrequency.value = frequency
  queueDigestPreferenceSave()
}

function saveDigestDayOfWeek(dayOfWeek: EmailDigestDayOfWeek) {
  if (dayOfWeek === emailDigestDayOfWeek.value) return
  rememberPendingDigestPreferenceBaseline()
  emailDigestDayOfWeek.value = dayOfWeek
  queueDigestPreferenceSave()
}

function updateSessionDigestPreferences(preferences: EmailDigestPreferences) {
  sessionUser.email_digest_frequency = preferences.email_digest_frequency
  sessionUser.email_digest_day_of_week = preferences.email_digest_day_of_week
}

function applyLocalDigestPreferences(preferences: EmailDigestPreferences) {
  emailDigestFrequency.value = preferences.email_digest_frequency
  emailDigestDayOfWeek.value = preferences.email_digest_day_of_week
}

function queueDigestPreferenceSave() {
  if (!sessionUser.user_profile) return
  clearPendingDigestPreferenceSave()
  if (hasReturnedToPendingDigestPreferenceBaseline() || !hasUnsavedDigestPreferences()) {
    pendingDigestPreferenceBaseline.value = null
    return
  }
  digestPreferenceSaveTimeout.value = window.setTimeout(() => {
    digestPreferenceSaveTimeout.value = null
    pendingDigestPreferenceBaseline.value = null
    saveDigestPreference()
  }, DIGEST_PREFERENCE_SAVE_DEBOUNCE_MS)
}

function clearPendingDigestPreferenceSave() {
  if (digestPreferenceSaveTimeout.value === null) return
  window.clearTimeout(digestPreferenceSaveTimeout.value)
  digestPreferenceSaveTimeout.value = null
}

function flushPendingDigestPreferenceSave() {
  clearPendingDigestPreferenceSave()
  pendingDigestPreferenceBaseline.value = null
  void saveDigestPreference()
}

async function saveDigestPreference() {
  if (!sessionUser.user_profile || !hasUnsavedDigestPreferences()) return

  if (isSavingDigestPreference.value) {
    shouldSaveAfterCurrentRequest.value = true
    return
  }

  let preferences = getLocalDigestPreferences()
  isSavingDigestPreference.value = true

  try {
    // setValue.submit resolves to void; the values we sent are exactly what got
    // persisted, so treat the submitted snapshot as the saved state.
    await userProfiles.setValue.submit({
      name: sessionUser.user_profile,
      ...preferences,
    })
    savedDigestPreferences.value = preferences
    updateSessionDigestPreferences(preferences)
    if (hasSameDigestPreferences(preferences, getLocalDigestPreferences())) {
      toast.success('Email digest preference saved', { id: digestPreferenceToastId })
    }
  } catch {
    pendingDigestPreferenceBaseline.value = null
    applyLocalDigestPreferences(savedDigestPreferences.value)
    toast.error('Could not save email digest preference', { id: digestPreferenceToastId })
  } finally {
    isSavingDigestPreference.value = false
    if (shouldSaveAfterCurrentRequest.value || hasUnsavedDigestPreferences()) {
      shouldSaveAfterCurrentRequest.value = false
      queueDigestPreferenceSave()
    }
  }
}

type EmailDigestPreferences = {
  email_digest_frequency: EmailDigestFrequency
  email_digest_day_of_week: EmailDigestDayOfWeek
}

function getLocalDigestPreferences(): EmailDigestPreferences {
  return {
    email_digest_frequency: emailDigestFrequency.value,
    email_digest_day_of_week: emailDigestDayOfWeek.value,
  }
}

function getSessionDigestPreferences(): EmailDigestPreferences {
  return {
    email_digest_frequency: getSessionDigestFrequency(),
    email_digest_day_of_week: getSessionDigestDayOfWeek(),
  }
}

function getSessionDigestFrequency(): EmailDigestFrequency {
  return sessionUser.email_digest_frequency || 'Off'
}

function getSessionDigestDayOfWeek(): EmailDigestDayOfWeek {
  return sessionUser.email_digest_day_of_week || 'Monday'
}

function hasUnsavedDigestPreferences() {
  return !hasSameDigestPreferences(getLocalDigestPreferences(), savedDigestPreferences.value)
}

function rememberPendingDigestPreferenceBaseline() {
  if (pendingDigestPreferenceBaseline.value) return
  pendingDigestPreferenceBaseline.value = getLocalDigestPreferences()
}

function hasReturnedToPendingDigestPreferenceBaseline() {
  return (
    !!pendingDigestPreferenceBaseline.value &&
    hasSameDigestPreferences(getLocalDigestPreferences(), pendingDigestPreferenceBaseline.value)
  )
}

function hasSameDigestPreferences(left: EmailDigestPreferences, right: EmailDigestPreferences) {
  return (
    left.email_digest_frequency === right.email_digest_frequency &&
    left.email_digest_day_of_week === right.email_digest_day_of_week
  )
}
</script>
