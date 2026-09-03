import { useDoc } from 'frappe-ui'
import { GPTask } from '@/types/doctypes'
import { createSharedDoc } from './sharedDoc'

interface Task extends GPTask {}

interface TaskMethods {
  trackVisit: () => void
}

/** The task behind `taskId`, followed as that id changes. */
export const useTask = createSharedDoc((name: string) =>
  useDoc<Task, TaskMethods>({
    doctype: 'GP Task',
    name,
    methods: {
      trackVisit: 'track_visit',
    },
    transform(doc) {
      return {
        ...doc,
        project: doc.project ? String(doc.project) : undefined,
      }
    },
  }),
)
