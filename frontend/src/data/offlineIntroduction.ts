import { watch } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { dialog } from 'frappe-ui'
import { isMobileViewport } from '@/utils/useIsMobile'
import { downloadForOffline, offlineWindow } from './offlineDownloads'
import { isOnline } from './online'
import { session } from './session'
import { useSessionUser } from './users'

/** Anchor for the Offline section of Settings > Preferences. */
export const OFFLINE_SECTION_ID = 'offline-settings'

const introduction = useLocalStorage<'new' | 'seen-offline' | 'done'>(
  `gameplan:offline-intro:${session.user}`,
  'new',
)

/**
 * Offers downloads once per account on a device: armed by going offline, shown on the next
 * load rather than on reconnect, where it would land on whatever the person was doing.
 */
export function setupOfflineIntroduction() {
  watch(isOnline, (online) => {
    if (online || offlineWindow.value || introduction.value !== 'new') return
    introduction.value = 'seen-offline'
  })
  if (introduction.value === 'seen-offline') setTimeout(offerDownload, 3000)
}

function offerDownload() {
  // A guest joins no communities, so there is nothing to download.
  if (offlineWindow.value || !isOnline.value || useSessionUser().isGuest) return
  introduction.value = 'done'
  const settings = isMobileViewport() ? 'More > Offline' : 'Settings > Preferences'
  dialog.confirm({
    title: 'Read Gameplan offline',
    message: `Keep discussions from the past month in your communities on this device, so they open even without a connection. You can change this in ${settings}.`,
    confirmLabel: 'Download',
    cancelLabel: 'Not now',
    onConfirm: () => {
      downloadForOffline(30)
      openOfflineSettings()
    },
  })
}

function openOfflineSettings() {
  // Imported on demand: both modules import this one.
  if (isMobileViewport()) {
    import('@/router').then(({ default: router }) => router.push({ name: 'OfflineSettings' }))
  } else {
    import('@/components/Settings').then(({ showSettingsDialog }) => {
      showSettingsDialog('Preferences')
      scrollToOfflineSection()
    })
  }
}

function scrollToOfflineSection(attemptsLeft = 20) {
  const section = document.getElementById(OFFLINE_SECTION_ID)
  if (section) {
    section.scrollIntoView({ block: 'start', behavior: 'smooth' })
    return
  }
  if (attemptsLeft) requestAnimationFrame(() => scrollToOfflineSection(attemptsLeft - 1))
}
