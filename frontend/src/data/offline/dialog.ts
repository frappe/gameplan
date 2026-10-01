/**
 * frappe-ui's `dialog`, refused offline before it opens rather than after its confirm fails.
 * Nearly every confirm ends in a write; one that only touches this device (discarding an
 * edit, removing downloads) passes `worksOffline`. A refused dialog counts as cancelled, so
 * callers waiting on `onCancel` still settle.
 */
import { dialog as frappeDialog } from 'frappe-ui'
import { refuseOffline } from './requests'

type ConfirmArgs = Parameters<typeof frappeDialog.confirm>[0]
type DangerArgs = Parameters<typeof frappeDialog.danger>[0]
type Offline<T> = T & { worksOffline?: boolean }

function guarded<T extends { onCancel?: () => void }>(open: (args: T) => unknown) {
  return ({ worksOffline, ...args }: Offline<T>) => {
    if (!worksOffline && refuseOffline()) return args.onCancel?.()
    open(args as T)
  }
}

export const dialog = {
  confirm: guarded<ConfirmArgs>(frappeDialog.confirm),
  danger: guarded<DangerArgs>(frappeDialog.danger),
}
