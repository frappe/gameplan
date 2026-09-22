<template>
  <div class="divide-y divide-outline-gray-1">
    <SettingsRow
      title="Download for offline"
      description="Keep discussions from Spaces you've joined on this device, with their comments and polls"
    >
      <!-- Offline there is nothing to download; Remove downloads below still works. -->
      <Select
        :options="windowOptions"
        v-model="selectedWindow"
        :disabled="!isOnline || downloads.syncing"
      />
    </SettingsRow>

    <!-- Nothing to say about the device until a window is picked: "Recently viewed only"
         downloads nothing and keeps nothing. -->
    <div v-if="offlineWindow">
      <SettingsRow title="On this device" :description="status" />
      <Progress v-if="downloads.syncing" class="pb-3.5" :value="progress" size="sm" />
      <div class="flex flex-wrap gap-2 pb-3.5">
        <Button :disabled="!isOnline || downloads.syncing" @click="confirmSync">Sync now</Button>
        <Button v-if="downloads.count" :disabled="downloads.syncing" @click="removeDownloads">
          Remove downloads
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Button, Progress, Select, SettingsRow, dayjsLocal, dialog } from 'frappe-ui'
import { isOnline } from '@/data/online'
import {
  MAX_DISCUSSIONS,
  WINDOW_OPTIONS,
  downloadForOffline,
  downloads,
  offlineWindow,
  removeOfflineDownloads,
  type OfflineWindow,
} from '@/data/offlineDownloads'

const windowOptions = WINDOW_OPTIONS.map((option) => ({
  label: option.label,
  value: String(option.value),
}))

// The Select keeps showing the current window until a choice is confirmed: the getter reads
// `offlineWindow`, which only the dialog's onConfirm changes.
const selectedWindow = computed({
  get: () => String(offlineWindow.value),
  set: (value: string) => confirmWindow(Number(value) as OfflineWindow),
})

function confirmWindow(days: OfflineWindow) {
  if (!days) return removeDownloads()
  const window = WINDOW_OPTIONS.find((option) => option.value === days)?.label.toLowerCase()
  dialog.confirm({
    title: 'Download offline?',
    message: `Discussions from the ${window} in Spaces you've joined will be kept on this device, with their comments and polls, and kept up to date in the background.`,
    confirmLabel: 'Download',
    cancelLabel: 'Cancel',
    onConfirm: () => downloadForOffline(days),
  })
}

function confirmSync() {
  dialog.confirm({
    title: 'Sync now?',
    message:
      'Gameplan will check for discussions that are new or have changed since the last sync, and download them.',
    confirmLabel: 'Sync',
    cancelLabel: 'Cancel',
    onConfirm: () => downloadForOffline(offlineWindow.value),
  })
}

const usedStorage = ref<string | null>(null)

async function readStorageUsage() {
  const estimate = await navigator.storage?.estimate?.().catch(() => null)
  usedStorage.value = estimate?.usage ? `${(estimate.usage / 1024 / 1024).toFixed(1)} MB` : null
}

onMounted(readStorageUsage)
// Downloading or removing changes what the browser holds, so the figure is read again
// rather than left at whatever it was when the panel opened.
watch([() => downloads.count, () => downloads.syncing], () => readStorageUsage())

const status = computed(() => {
  if (downloads.syncing) {
    return downloads.total
      ? `Downloading ${downloads.done} of ${downloads.total} discussions…`
      : 'Checking for changes…'
  }
  const parts = [downloaded()]
  if (downloads.lastSyncedAt) parts.push(`synced ${dayjsLocal(downloads.lastSyncedAt).fromNow()}`)
  // What the browser holds for the whole origin: the app's own files (~5 MB of build
  // output) as much as the downloads, and space it has not reclaimed yet. So it never reads
  // as zero, and a smaller window doesn't shrink it — hence "used by Gameplan" rather than
  // anything that sounds like the cost of the downloads.
  if (usedStorage.value) parts.push(`${usedStorage.value} used by Gameplan`)
  if (downloads.error) parts.push('last sync failed')
  return parts.join(' · ')
})

/** A busy site has more in the window than one device keeps, so say which it has. */
function downloaded() {
  if (downloads.count >= MAX_DISCUSSIONS) return `Newest ${MAX_DISCUSSIONS} discussions downloaded`
  if (downloads.count === 1) return '1 discussion downloaded'
  return `${downloads.count} discussions downloaded`
}

const progress = computed(() =>
  downloads.total ? Math.round((downloads.done / downloads.total) * 100) : 0,
)

function removeDownloads() {
  dialog.confirm({
    title: 'Remove offline downloads?',
    message:
      'Downloaded discussions will no longer open without a connection until you open them again online.',
    confirmLabel: 'Remove',
    cancelLabel: 'Cancel',
    onConfirm: async () => {
      offlineWindow.value = 0
      await removeOfflineDownloads()
    },
  })
}
</script>
