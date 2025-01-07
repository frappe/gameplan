import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { GPTask } from '@/types/doctypes'

let tasksCache: Record<string, ReturnType<typeof useDoc>> = {}

export function useTask(taskId: MaybeRefOrGetter<string>) {
  interface Task extends GPTask {}

  interface TaskMethods {
    trackVisit: () => void
  }

  let name = toValue(taskId)
  if (!tasksCache[name]) {
    tasksCache[name] = useDoc<Task, TaskMethods>({
      doctype: 'GP Task',
      name: taskId,
      methods: {
        trackVisit: 'track_visit',
      },
    })
  }
  return tasksCache[name] as ReturnType<typeof useDoc<Task, TaskMethods>>
}
