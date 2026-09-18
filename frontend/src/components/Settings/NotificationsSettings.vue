<template>
  <SettingsHeader>
    <h2 class="text-lg-semibold text-ink-gray-8">Notifications</h2>
  </SettingsHeader>

  <SettingsBody>
    <div class="space-y-11 pt-6">
      <section>
        <h3 class="mb-2 text-base-medium text-ink-gray-8">How and when to reach me</h3>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow
            title="Receive notifications"
            :description="
              receiveNotifications
                ? `Push and email reach you between these times on these days, in ${timezoneLabel}`
                : 'Push and email are held; a card recaps what you missed when you switch back on'
            "
          >
            <Switch
              :model-value="receiveNotifications"
              @update:model-value="setReceiveNotifications"
            />
          </SettingsRow>

          <!-- The hours unfold under the switch: all day, every day until narrowed, so
               there is nothing to turn on. Native time inputs: hour, minute and am/pm are
               each a segment you click and step; the browser's clock popup is hidden
               (index.css) so there is no endless list to scroll. -->
          <!-- Part of the row above, so no divider between them (the section's divide-y
               would draw one). -->
          <div v-if="receiveNotifications" class="space-y-3 pb-4 !border-t-0">
            <div class="flex flex-wrap items-center gap-2 text-base text-ink-gray-7">
              <span>From</span>
              <TextInput
                type="time"
                class="active-hours-time w-[6.5rem]"
                :model-value="activeHoursStart"
                @update:model-value="(value: string) => setActiveHours({ start: value })"
              />
              <span>to</span>
              <TextInput
                type="time"
                class="active-hours-time w-[6.5rem]"
                :model-value="activeHoursEnd"
                @update:model-value="(value: string) => setActiveHours({ end: value })"
              />
              <span v-if="isOvernight" class="text-sm text-ink-gray-5">(next day)</span>
            </div>
            <!-- The last selected day cannot be unpicked: a schedule with no days is not a
                 schedule (the server refuses it too), and there is no other day to pick. -->
            <div class="flex flex-wrap gap-1.5" role="group" aria-label="Active days">
              <!-- Every day is a box: an unpicked one is outlined, a picked one filled with
                   the soft grey, so the row reads as seven toggles, none of them shouting. -->
              <Button
                v-for="day in allWeekdays"
                :key="day"
                size="sm"
                :variant="activeHoursDays.includes(day) ? 'subtle' : 'outline'"
                :aria-pressed="activeHoursDays.includes(day)"
                :disabled="activeHoursDays.length === 1 && activeHoursDays.includes(day)"
                :label="day"
                @click="toggleDay(day)"
              />
            </div>
          </div>

          <SettingsRow title="Reach me by" :description="channelDescription">
            <Select
              :options="channelOptions"
              :model-value="notificationChannel"
              @update:model-value="setNotificationChannel"
            />
          </SettingsRow>
        </div>
      </section>

      <section>
        <h3 class="mb-2 text-base-medium text-ink-gray-8">Notify me about</h3>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow title="From discussions" :description="notificationLevelDescription">
            <Select
              :options="notificationLevelOptions"
              :model-value="notificationLevel"
              @update:model-value="setNotificationLevel"
            />
          </SettingsRow>

          <SettingsRow
            title="Watch discussions I start"
            description="Get notified about every comment on discussions you open"
          >
            <Switch
              :model-value="watchOwnDiscussions"
              @update:model-value="setWatchOwnDiscussions"
            />
          </SettingsRow>

          <!-- The toggles live on the community's Spaces panel (one column per space);
               this row is the signpost for anyone who has not met them in a space menu. -->
          <SettingsRow
            v-if="communityState.id"
            title="Space notifications"
            description="Pick the spaces whose new discussions should reach you"
          >
            <Button label="Manage" @click="showCommunitiesSettings(communityState.id, 'spaces')" />
          </SettingsRow>
        </div>
      </section>

      <section>
        <h3 class="mb-2 text-base-medium text-ink-gray-8">Activity on my content</h3>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow
            title="Reactions"
            description="When someone reacts to your discussions, comments or polls"
          >
            <Switch :model-value="notifyReactions" @update:model-value="setNotifyReactions" />
          </SettingsRow>

          <SettingsRow title="Poll votes" description="When someone votes on a poll you created">
            <Switch :model-value="notifyPollVotes" @update:model-value="setNotifyPollVotes" />
          </SettingsRow>
        </div>
      </section>

      <section>
        <h3 class="mb-2 text-base-medium text-ink-gray-8">Summary email</h3>
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
  Button,
  dayjsLocal,
  getConfig,
  Select,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  Switch,
  TextInput,
  toast,
  useDoctype,
} from 'frappe-ui'
import { showCommunitiesSettings } from '@/components/Settings'
import { communityState } from '@/data/communityState'
import { useSessionUser, type EmailDigestDayOfWeek, type EmailDigestFrequency } from '@/data/users'
import {
  allWeekdays,
  currentActiveHoursDays as activeHoursDays,
  currentActiveHoursEnd as activeHoursEnd,
  currentActiveHoursStart as activeHoursStart,
  currentNotificationChannel as notificationChannel,
  currentNotificationLevel as notificationLevel,
  currentNotifyPollVotes as notifyPollVotes,
  currentNotifyReactions as notifyReactions,
  currentReceiveNotifications as receiveNotifications,
  currentWatchOwnDiscussions as watchOwnDiscussions,
  setActiveHours,
  setNotificationChannel,
  setNotificationLevel,
  setNotifyPollVotes,
  setNotifyReactions,
  setReceiveNotifications,
  setWatchOwnDiscussions,
  type NotificationChannel,
  type NotificationLevel,
  type Weekday,
} from '@/data/notificationPreferences'
import type { GPUserProfile } from '@/types/doctypes'

const sessionUser = useSessionUser()

const notificationLevelOptions: Array<{ value: NotificationLevel; label: NotificationLevel }> = [
  { value: 'Mentions only', label: 'Mentions only' },
  { value: 'Mute', label: 'Mute' },
]

// The description does the explaining, so the control can stay a plain Select. It says
// what the current choice means; the Mute wording answers the "but I was mentioned"
// report before it is filed.
const notificationLevelDescription = computed(() =>
  notificationLevel.value === 'Mute'
    ? "Nothing reaches you from discussions you haven't set a bell on — not even mentions."
    : 'Mentions reach you from every discussion.',
)
// Push joins this list once the relay exists (Phase 5); until then it is not offered.
const channelOptions: Array<{ value: NotificationChannel; label: string }> = [
  { value: 'In-app', label: 'In-app only' },
  { value: 'Email', label: 'Email' },
]
const channelDescription = computed(() =>
  notificationChannel.value === 'Email'
    ? 'One email an hour with everything new since the last one, on top of the inbox'
    : 'The inbox and the bell only; nothing leaves Gameplan',
)

// The schedule is kept in the user's own zone on the server (User.time_zone, else the
// site's); this names the one the browser is in, which is what the user set it by.
const timezoneLabel =
  getConfig('localTimezone') || Intl.DateTimeFormat().resolvedOptions().timeZone || 'local time'
// 23:59 is "end of day", not a wrap into tomorrow (the server reads it the same way).
const isOvernight = computed(
  () => activeHoursEnd.value < activeHoursStart.value && activeHoursEnd.value !== '23:59',
)

function toggleDay(day: Weekday) {
  const days = activeHoursDays.value.includes(day)
    ? activeHoursDays.value.filter((d) => d !== day)
    : allWeekdays.filter((d) => d === day || activeHoursDays.value.includes(d))
  if (days.length) setActiveHours({ days })
}

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
