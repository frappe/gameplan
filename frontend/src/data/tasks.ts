import { MaybeRefOrGetter, toValue } from 'vue'
import { toast, useDoc } from 'frappe-ui'
import { GPTask } from '@/types/doctypes'
import { OptimisticSave } from '@/utils/optimisticSave'
import { revalidateOnReconnect } from '@/data/offline/resources'

interface Task extends GPTask {}

interface TaskMethods {
  trackVisit: () => void
}

type TaskResource = ReturnType<typeof useDoc<Task, TaskMethods>>

interface CachedTask {
  resource: TaskResource
  // Lives as long as the resource, so a page opened again while a move is in flight
  // queues behind that move instead of racing it.
  spaceMove: OptimisticSave<string | undefined>
}

let tasksCache: Record<string, CachedTask> = {}

export function useTask(taskId: MaybeRefOrGetter<string>) {
  const cached = tasksCache[toValue(taskId)]
  return cached ? revalidateOnReconnect(cached.resource) : cachedTask(taskId).resource
}

/** Moves a task to another space, one save at a time. */
export function useTaskSpaceMove(taskId: MaybeRefOrGetter<string>) {
  return cachedTask(taskId).spaceMove
}

function cachedTask(taskId: MaybeRefOrGetter<string>) {
  let name = toValue(taskId)
  if (!tasksCache[name]) {
    let resource = useDoc<Task, TaskMethods>({
      doctype: 'GP Task',
      name: taskId,
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
    tasksCache[name] = { resource, spaceMove: createSpaceMove(resource) }
  }
  return tasksCache[name]
}

function createSpaceMove(task: TaskResource) {
  // Shown through `spaceMove.shown(task.doc.project)`. Writing to `task.doc` would not
  // reach the screen: `transform` makes `doc` a fresh copy, not the stored document.
  return new OptimisticSave<string | undefined>({
    send: (spaceId) => task.setValue.submit({ project: spaceId }),
    onError: () => toast.error('Could not save the task'),
  })
}
