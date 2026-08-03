import { dialog, toast } from 'frappe-ui'
import { getServerErrorMessage, isPermissionError } from '@/utils/errorMessage'

/**
 * Asks before throwing away a saved layout, then reports how it went.
 *
 * Two screens offer this — the customize panel and the profile page's empty
 * state — and they share the words so one action cannot describe its
 * consequences two different ways. Each passes its own `restore`, because what
 * has to be refreshed afterwards is the caller's own read path.
 *
 * @param hasUnsavedChanges Say so when a draft goes too. The leave-guard's own
 * question never gets asked here, because restoring is not leaving.
 */
export function confirmRestoreDefaultLayout(
  restore: () => void | Promise<void>,
  { hasUnsavedChanges = false }: { hasUnsavedChanges?: boolean } = {},
) {
  let message =
    'Your saved layout will be discarded and your profile page will follow the default again. Your profile info is not affected.'
  if (hasUnsavedChanges) {
    message += ' Any unsaved changes to the layout go with it.'
  }

  // `confirm`, not `danger`: the profile screens stay on gray, with no red anywhere.
  dialog.confirm({
    title: 'Restore default layout',
    message,
    confirmLabel: 'Restore default',
    cancelLabel: 'Keep my layout',
    onConfirm: async () => {
      try {
        await restore()
        toast.success('Default layout restored')
      } catch (error) {
        toast.error(getRestoreErrorMessage(error))
      }
    },
  })
}

function getRestoreErrorMessage(error: unknown) {
  if (isPermissionError(error)) {
    return 'You do not have permission to change this profile layout'
  }
  return getServerErrorMessage(error) || 'Could not restore the default layout'
}
