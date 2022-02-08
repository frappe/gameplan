import { h, reactive, ref } from 'vue'
import { Dialog } from 'frappe-ui'

let dialogs = ref([])

export let Dialogs = {
  name: 'Dialogs',
  render() {
    return dialogs.value.map((dialog) =>
      h(Dialog, {
        options: dialog,
        modelValue: dialog.show,
        'onUpdate:modelValue': (val) => (dialog.show = val),
      })
    )
  },
}

export function createDialog(dialogOptions) {
  let dialog = reactive({
    key: 'dialog-' + dialogs.value.length,
    show: false,
    ...dialogOptions,
  })
  setTimeout(() => {
    dialog.show = true
  }, 0)
  dialogs.value.push(dialog)
}
