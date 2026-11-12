import { dialog } from 'frappe-ui'
import { errorText } from '@/utils'

/**
 * Asks before deleting something, per the app's confirm rule: a question as the title,
 * one sentence on the effect, Cancel and a red Delete. Custom actions instead of
 * `theme: 'red'` because the theme also puts a warning icon in the title.
 */
export function confirmDelete(options: {
  title: string
  message: string
  onDelete: () => Promise<unknown>
}) {
  dialog.confirm({
    title: options.title,
    message: options.message,
    actions: [
      { label: 'Cancel', variant: 'outline' },
      {
        label: 'Delete',
        variant: 'solid',
        theme: 'red',
        onClick: async () => {
          // A rejection keeps the dialog open with the error in it; make that error readable.
          await options.onDelete().catch((error: unknown) => {
            throw new Error(errorText(error, "Couldn't delete it. Try again."))
          })
        },
      },
    ],
  })
}
