import { GPTask } from '@/types/doctypes'
import { useNewDoc } from 'frappe-ui/src/data-fetching'
import { ref } from 'vue'

export const showDialog = ref(false)
export const newTask = ref<ReturnType<typeof newDraftTask> | null>(null)
export const _onSuccess = ref<(doc: GPTask) => void>(() => {})

export function showNewTaskDialog({ defaults = {}, onSuccess = (doc: GPTask) => {} } = {}) {
  newTask.value = newDraftTask()
  Object.assign(newTask.value.doc, defaults || {})
  showDialog.value = true
  _onSuccess.value = onSuccess
}

function newDraftTask() {
  return useNewDoc<GPTask>('GP Task', {
    title: '',
    description: '',
    status: 'Backlog',
    assigned_to: '',
    project: '',
  })
}
