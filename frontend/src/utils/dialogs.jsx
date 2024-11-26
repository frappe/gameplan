import { h, reactive, ref, computed } from 'vue'
import { Dialog, ErrorMessage } from 'frappe-ui'

let dialogs = ref([])

export let Dialogs = {
  name: 'Dialogs',
  render() {
    return dialogs.value.map((dialog) => (
      <Dialog
        options={dialog}
        modelValue={dialog.show}
        onUpdate:modelValue={(val) => (dialog.show = val)}
      >
        {{
          'body-content': () => {
            return [
              dialog.message && <p class="text-p-base text-ink-gray-7">{dialog.message}</p>,
              <ErrorMessage class="mt-2" message={dialog.error} />,
            ]
          },
        }}
      </Dialog>
    ))
  },
}

export function createDialog(dialogOptions) {
  let dialog = reactive(dialogOptions)
  dialog.key = 'dialog-' + dialogs.value.length
  dialog.show = false
  setTimeout(() => {
    dialog.show = true
  }, 0)
  dialogs.value.push(dialog)
}
