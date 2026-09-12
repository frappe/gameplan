import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc } from 'frappe-ui'
import { GPTask } from '@/types/doctypes'

let tasksCache: Record<string, ReturnType<typeof useDoc>> = {}

interface Task extends GPTask {}

interface TaskMethods {
  trackVisit: () => void
}

export function useTask(taskId: MaybeRefOrGetter<string>) {
  let name = toValue(taskId)
  if (!tasksCache[name]) {
    tasksCache[name] = useDoc<Task, TaskMethods>({
      doctype: 'GP Task',
      name: taskId,
      staleOnError: true,
      methods: {
        trackVisit: 'track_visit',
      },
      transform(doc) {
        return {
          ...doc,
          project: doc.project ? String(doc.project) : undefined,
        }
      },
    })
  }
  return tasksCache[name] as ReturnType<typeof useDoc<Task, TaskMethods>>
}
