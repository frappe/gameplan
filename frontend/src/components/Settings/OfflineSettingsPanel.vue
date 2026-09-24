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
import { computed } from 'vue'
import { computedAsync } from '@vueuse/core'
import { Button, Progress, Select, SettingsRow, dayjsLocal, dialog } from 'frappe-ui'
import { isOnline } from '@/data/online'
import {
  MAX_DISCUSSIONS,
  WINDOW_OPTIONS,
  downloadForOffline,
  downloadedBytes,
  downloads,
  offlineWindow,
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

// Read again whenever a sync, a removal or the worker's image saves change what is held.
const size = computedAsync(async () => {
  void [downloads.count, downloads.syncing, downloads.imagesSavedAt]
  const bytes = await downloadedBytes().catch(() => 0)
  if (!bytes) return null
  return bytes < 1024 * 1024
    ? `${Math.round(bytes / 1024)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}, null)

const status = computed(() => {
  if (downloads.syncing) {
    return downloads.total
      ? `Downloading ${downloads.done} of ${downloads.total} discussions…`
      : 'Checking for changes…'
  }
  const parts = [downloaded()]
  if (downloads.lastSyncedAt) parts.push(`synced ${dayjsLocal(downloads.lastSyncedAt).fromNow()}`)
  // The downloads themselves: the discussions with their comments, activity and polls, and
  // the images saved with them. Not the app's own files, which are not the person's to keep.
  if (size.value) parts.push(`taking ${size.value}`)
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
    onConfirm: () => downloadForOffline(0),
  })
}
</script>
