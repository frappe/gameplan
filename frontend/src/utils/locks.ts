/** Web Locks across tabs, with a queue in this tab when they are unavailable. */
const queues = new Map<string, Promise<unknown>>()

export async function withLock<T>(
  name: string,
  task: (available: boolean) => T | Promise<T>,
  ifAvailable = false,
): Promise<T> {
  if (navigator.locks)
    return navigator.locks.request(name, { ifAvailable }, (lock) => task(Boolean(lock)))
  if (ifAvailable && queues.has(name)) return task(false)
  const previous = queues.get(name)?.catch(() => {})
  const run = (previous ?? Promise.resolve()).then(() => task(true))
  queues.set(name, run)
  return run.finally(() => {
    if (queues.get(name) === run) queues.delete(name)
  })
}
