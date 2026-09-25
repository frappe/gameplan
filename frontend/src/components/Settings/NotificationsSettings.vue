<template>
  <PanelHeader title="Notifications" />

  <PanelBody>
    <div class="space-y-7 pt-6">
      <section>
        <div class="divide-y divide-outline-gray-1">
          <!-- SettingsRow's shape, written out because its description is plain text and
               this one carries the Change link: "Thursdays, all day · Asia/Gaza · Change". -->
          <div class="flex items-center gap-8 py-3.5" :class="editingSchedule && '!pb-1'">
            <div class="min-w-0 flex-1">
              <div class="text-base-medium text-ink-gray-8">Receive notifications</div>
              <div class="mt-1 text-base leading-5 text-ink-gray-6">
                <template v-if="receiveNotifications">
                  {{ scheduleSummary }} · {{ timezoneLabel }}
                </template>
                <template v-else>
                  Email is held; you get a catch-up email when you switch back on
                </template>
              </div>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <Button
                v-if="receiveNotifications"
                :label="editingSchedule ? 'Done' : 'Change'"
                @click="editingSchedule = !editingSchedule"
              />
              <Switch
                :model-value="receiveNotifications"
                @update:model-value="setReceiveNotifications"
              />
            </div>
          </div>

          <!-- The hours unfold under the switch: all day, every day until narrowed, so
               there is nothing to turn on. Native time inputs: hour, minute and am/pm are
               each a segment you click and step; the browser's clock popup is hidden
               (index.css) so there is no endless list to scroll. -->
          <!-- Two rows in the page's own shape — label left, control right — but read as
               part of the switch's row: no dividers, tighter, with the sub-labels in the muted
               body weight rather than a row title's. -->
          <template v-if="receiveNotifications && editingSchedule">
            <SettingsRow
              title="Hours"
              class="!border-t-0 !py-2 [&>div:first-child>*]:!text-base [&>div:first-child>*]:!font-normal [&>div:first-child>*]:!text-ink-gray-7"
            >
              <div class="flex flex-wrap items-center justify-end gap-2 text-base text-ink-gray-7">
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
            </SettingsRow>

            <!-- The last selected day cannot be unpicked: a schedule with no days is not a
                 schedule (the server refuses it too), and there is no other day to pick. -->
            <SettingsRow
              title="Days"
              class="!border-t-0 !pb-4 !pt-2 [&>div:first-child>*]:!text-base [&>div:first-child>*]:!font-normal [&>div:first-child>*]:!text-ink-gray-7"
            >
              <div class="flex flex-wrap justify-end gap-1.5" role="group" aria-label="Active days">
                <!-- Seven toggles: a picked day is the solid button, an unpicked one the soft
                     grey, so the picked set reads at a glance without any borders. The last
                     picked day is not disabled — a disabled solid button greys out and reads
                     as unpicked — it simply ignores the click (toggleDay keeps one day). -->
                <Button
                  v-for="day in allWeekdays"
                  :key="day"
                  size="sm"
                  :variant="activeHoursDays.includes(day) ? 'solid' : 'subtle'"
                  :aria-pressed="activeHoursDays.includes(day)"
                  :label="day"
                  @click="toggleDay(day)"
                />
              </div>
            </SettingsRow>
          </template>

          <SettingsRow
            v-if="receiveNotifications"
            title="Notify me by"
            description="Choose where you get your notifications"
          >
            <Select
              :options="channelOptions"
              :model-value="notificationChannel"
              @update:model-value="setNotificationChannel"
            />
          </SettingsRow>

          <SettingsRow
            title="Notifications for discussions you're part of"
            description="Choose notifications for discussions you started or joined"
          >
            <Select
              :options="participationOptions"
              :model-value="participationLevel"
              @update:model-value="setParticipationLevel"
            />
          </SettingsRow>

          <SettingsRow
            v-if="communityState.id"
            title="Space notifications"
            description="Pick the spaces whose new discussions should reach you"
          >
            <Button label="Manage" @click="showCommunitiesSettings(communityState.id, 'spaces')" />
          </SettingsRow>

          <SettingsRow title="Enable email digests" :description="emailDigestDescription">
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
        </div>
      </section>
    </div>
  </PanelBody>
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
  SettingsRow,
  Switch,
  TextInput,
  toast,
  useDoctype,
} from 'frappe-ui'
import PanelHeader from './PanelHeader.vue'
import PanelBody from './PanelBody.vue'
import { showCommunitiesSettings } from '@/components/Settings'
import { communityState } from '@/data/communityState'
import { useSessionUser, type EmailDigestDayOfWeek, type EmailDigestFrequency } from '@/data/users'
import {
  allDayEnd,
  allDayStart,
  allWeekdays,
  currentActiveHoursDays as activeHoursDays,
  currentActiveHoursEnd as activeHoursEnd,
  currentActiveHoursStart as activeHoursStart,
  currentNotificationChannel as notificationChannel,
  currentParticipationLevel as participationLevel,
  currentReceiveNotifications as receiveNotifications,
  setActiveHours,
  setNotificationChannel,
  setParticipationLevel,
  setReceiveNotifications,
  type NotificationChannel,
  type ParticipationLevel,
  type Weekday,
} from '@/data/notificationPreferences'
import type { GPUserProfile } from '@/types/doctypes'

const sessionUser = useSessionUser()

// Push joins this list once the relay exists (Phase 5); until then it is not offered.
const channelOptions: Array<{ value: NotificationChannel; label: string }> = [
  { value: 'In-app', label: 'In-app only' },
  { value: 'Email', label: 'Email' },
]
const participationOptions: Array<{ value: ParticipationLevel; label: string }> = [
  { value: 'Watch', label: 'Watch' },
  { value: 'Mentions only', label: 'Mentions only' },
]

// The schedule runs in the timezone from Preferences (User.time_zone), falling back to the
// site's when none is set — the same rule the server applies.
const timezoneLabel = computed(
  () => sessionUser.time_zone || getConfig('systemTimezone') || 'the site timezone',
)
// 23:59 is "end of day", not a wrap into tomorrow (the server reads it the same way).
const editingSchedule = ref(false)

// "Thursdays, all day" / "Weekdays, 9:00 AM – 6:00 PM" / "Every day, all day".
const dayNames: Record<Weekday, string> = {
  Mon: 'Mondays',
  Tue: 'Tuesdays',
  Wed: 'Wednesdays',
  Thu: 'Thursdays',
  Fri: 'Fridays',
  Sat: 'Saturdays',
  Sun: 'Sundays',
}
const scheduleSummary = computed(() => {
  const allDay = activeHoursStart.value === allDayStart && activeHoursEnd.value === allDayEnd
  const hours = allDay
    ? 'all day'
    : `${clockLabel(activeHoursStart.value)} – ${clockLabel(activeHoursEnd.value)}`
  const picked = new Set(activeHoursDays.value)
  const same = (list: Weekday[]) => list.length === picked.size && list.every((d) => picked.has(d))
  const chosen = allWeekdays.filter((d) => picked.has(d))
  const days = same(allWeekdays)
    ? 'Every day'
    : same(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
      ? 'Weekdays'
      : same(['Sat', 'Sun'])
        ? 'Weekends'
        : chosen.length === 1
          ? dayNames[chosen[0]]
          : chosen.join(', ')
  return `${days}, ${hours}`
})

function clockLabel(time: string) {
  return dayjsLocal(`2000-01-01T${time}`).format('h:mm A')
}

const isOvernight = computed(
  () => activeHoursEnd.value < activeHoursStart.value && activeHoursEnd.value !== '23:59',
)

function toggleDay(day: Weekday) {
  const days = activeHoursDays.value.includes(day)
    ? activeHoursDays.value.filter((d) => d !== day)
    : allWeekdays.filter((d) => d === day || activeHoursDays.value.includes(d))
  if (!days.length) {
    toast.error('Keep at least one day, or turn Receive notifications off instead', {
      id: 'active-days-minimum',
    })
    return
  }
  setActiveHours({ days })
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
// The last send date rides on the switch's own description rather than a row of its own.
const emailDigestDescription = computed(() => {
  const lastSent = sessionUser.email_digest_last_sent_on
    ? `Last sent ${dayjsLocal(sessionUser.email_digest_last_sent_on).format('D MMM YYYY')}`
    : 'Not sent yet'
  return `Send a summary of missed activity. ${lastSent}`
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
