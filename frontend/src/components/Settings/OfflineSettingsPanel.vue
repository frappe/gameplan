<template>
  <div class="space-y-11">
    <section>
      <p v-if="!policy.enabled" class="text-p-base text-ink-gray-6">
        Offline downloads are turned off for this site. Discussions you open are still kept for
        offline reading.
      </p>
      <div v-else class="divide-y divide-outline-gray-1">
        <SettingsRow
          title="Download for offline"
          description="Keep discussions from spaces you've joined on this device, with their comments and polls"
        >
          <Select :options="windowOptions" v-model="selectedWindow" />
        </SettingsRow>

        <div>
          <SettingsRow title="On this device" :description="status" />
          <Progress v-if="downloads.syncing" class="pb-3.5" :value="progress" size="sm" />
          <div v-if="offlineWindow || downloads.count" class="flex flex-wrap gap-2 pb-3.5">
            <Button
              v-if="offlineWindow"
              :disabled="!isOnline || downloads.syncing"
              @click="downloadForOffline(offlineWindow)"
            >
              Sync now
            </Button>
            <Button v-if="downloads.count" :disabled="downloads.syncing" @click="removeDownloads">
              Remove downloads
            </Button>
          </div>
        </div>
      </div>
    </section>

    <section v-if="isGameplanAdmin()">
      <h2 class="text-lg-semibold text-ink-gray-8">Site</h2>
      <div class="mt-2 divide-y divide-outline-gray-1">
        <SettingsRow
          title="Allow offline downloads"
          description="Let people download recent discussions to read without a connection"
        >
          <Switch
            :model-value="policy.enabled"
            :disabled="!isOnline || savingPolicy"
            @update:model-value="(enabled: boolean) => savePolicy({ enabled })"
          />
        </SettingsRow>
        <SettingsRow
          title="Longest download window"
          description="The furthest back anyone can choose to download"
        >
          <Select
            :options="maxWindowOptions"
            :model-value="String(policy.maxWindow)"
            :disabled="!policy.enabled || !isOnline || savingPolicy"
            @update:model-value="(value: string) => savePolicy({ maxWindow: Number(value) })"
          />
        </SettingsRow>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Button,
  Progress,
  Select,
  SettingsRow,
  Switch,
  call,
  dayjsLocal,
  dialog,
  toast,
} from 'frappe-ui'
import { isOnline } from '@/data/online'
import { isGameplanAdmin } from '@/data/users'
import {
  WINDOW_OPTIONS,
  downloadForOffline,
  downloads,
  offlineWindow,
  policy,
  removeOfflineDownloads,
  type OfflineWindow,
} from '@/data/offlineDownloads'

const windowOptions = computed(() =>
  WINDOW_OPTIONS.filter((option) => option.value <= policy.maxWindow).map((option) => ({
    label: option.label,
    value: String(option.value),
  })),
)

const maxWindowOptions = WINDOW_OPTIONS.filter((option) => option.value).map((option) => ({
  label: option.label,
  value: String(option.value),
}))

const selectedWindow = computed({
  get: () => String(offlineWindow.value),
  set: (value: string) => downloadForOffline(Number(value) as OfflineWindow),
})

const usedStorage = ref<string | null>(null)
onMounted(async () => {
  const estimate = await navigator.storage?.estimate?.().catch(() => null)
  if (estimate?.usage) usedStorage.value = `${(estimate.usage / 1024 / 1024).toFixed(1)} MB`
})

const status = computed(() => {
  if (downloads.syncing) {
    return downloads.total
      ? `Downloading ${downloads.done} of ${downloads.total} discussions…`
      : 'Checking for changes…'
  }
  const parts = [
    downloads.count === 1 ? '1 discussion downloaded' : `${downloads.count} discussions downloaded`,
  ]
  if (downloads.lastSyncedAt) parts.push(`synced ${dayjsLocal(downloads.lastSyncedAt).fromNow()}`)
  if (usedStorage.value) parts.push(`${usedStorage.value} used by Gameplan`)
  if (downloads.error) parts.push('last sync failed')
  return parts.join(' · ')
})

const progress = computed(() =>
  downloads.total ? Math.round((downloads.done / downloads.total) * 100) : 0,
)

function removeDownloads() {
  dialog.confirm({
    title: 'Remove offline downloads?',
    message:
      'Downloaded discussions will no longer open without a connection until you open them again online.',
    confirmLabel: 'Remove',
    onConfirm: async () => {
      offlineWindow.value = 0
      await removeOfflineDownloads()
    },
  })
}

const savingPolicy = ref(false)
async function savePolicy(change: { enabled?: boolean; maxWindow?: number }) {
  savingPolicy.value = true
  try {
    await call('frappe.client.set_value', {
      doctype: 'GP Settings',
      name: 'GP Settings',
      fieldname: {
        enable_offline_downloads: (change.enabled ?? policy.enabled) ? 1 : 0,
        max_offline_window_days: String(change.maxWindow ?? policy.maxWindow),
      },
    })
    Object.assign(policy, change)
  } catch {
    toast.error('Could not save the offline download settings')
  } finally {
    savingPolicy.value = false
  }
}
</script>
