import { shallowRef } from 'vue'

interface OptimisticSaveOptions<T> {
  /** Saves a value on the server. */
  send: (value: T) => Promise<unknown>
  onError: () => void
}

/**
 * Shows a change at once and saves it, for a value the user can change again before
 * the server answers.
 *
 * One save is in flight at a time, so the server applies changes in the order they
 * were made. Changes made meanwhile wait, and only the latest one is sent next.
 *
 * The caller keeps the saved value and shows `shown(saved)`. Until the server
 * answers, that is the newest change. When nothing is left to send, it is the saved
 * value again: after a failure that is the last value the server accepted. So an old
 * failure never undoes a newer change, and a rollback never shows a value the server
 * did not accept.
 */
export class OptimisticSave<T> {
  // Wrapped, so that a change to `undefined` is still a change.
  private pending = shallowRef<{ value: T } | null>(null)
  private waiting: { value: T } | null = null
  private saving = false
  private savedCallbacks = new Set<(value: T) => void>()

  constructor(private options: OptimisticSaveOptions<T>) {}

  /** The value to show: the newest change the server has not answered, or `saved`. */
  shown(saved: T): T {
    return this.pending.value ? this.pending.value.value : saved
  }

  /** True while a save is in flight. A change waiting to be sent always has one ahead of it. */
  get busy() {
    return this.saving
  }

  /**
   * Calls `callback` after each successful save, before `shown()` goes back to the
   * saved value. Returns a function that stops it.
   */
  onSaved(callback: (value: T) => void) {
    this.savedCallbacks.add(callback)
    return () => {
      this.savedCallbacks.delete(callback)
    }
  }

  change(value: T) {
    this.pending.value = { value }
    this.waiting = { value }
    this.sendWaiting()
  }

  private sendWaiting() {
    if (this.saving || !this.waiting) return
    const { value } = this.waiting
    this.waiting = null
    this.saving = true
    this.options
      .send(value)
      .then(
        () => this.saved(value),
        () => this.failed(),
      )
      .finally(() => {
        this.saving = false
        this.sendWaiting()
      })
  }

  private saved(value: T) {
    this.savedCallbacks.forEach((callback) => callback(value))
    if (!this.waiting) this.pending.value = null
  }

  private failed() {
    if (!this.waiting) this.pending.value = null
    this.options.onError()
  }
}
