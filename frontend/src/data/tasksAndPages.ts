import { computed, ref } from 'vue'
import { useDoctype } from 'frappe-ui'

// The site-wide GP Settings switch for the deprecated Tasks and Pages. The boot data
// carries the saved value. A save here updates it in place, so the admin who flips the
// switch sees the tabs change without a reload. Read lazily: in dev the boot values
// reach `window` after this module loads.
const savedValue = ref<boolean | null>(null)

export const tasksAndPagesEnabled = computed(
  () => savedValue.value ?? Boolean(window.enable_tasks_and_pages),
)

const settings = useDoctype('GP Settings')

export async function setTasksAndPagesEnabled(enabled: boolean) {
  await settings.setValue.submit({
    name: 'GP Settings',
    enable_tasks_and_pages: enabled ? 1 : 0,
  })
  savedValue.value = enabled
}
