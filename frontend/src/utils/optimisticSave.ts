interface OptimisticSaveOptions<T> {
  /** The value on screen. */
  read: () => T
  /** Puts a value on screen. */
  write: (value: T) => void
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
 * `confirmed` is the last value the server accepted. A failed save puts it back on
 * screen, unless a newer change is waiting: that change stays and is sent next. So
 * an old failure never undoes a newer change, and a rollback never shows a value the
 * server did not accept.
 */
export class OptimisticSave<T> {
  // Set by change() before the first save is sent.
  private confirmed!: T
  private waiting: { value: T } | null = null
  private saving = false
  private savedCallbacks = new Set<(value: T) => void>()

  constructor(private options: OptimisticSaveOptions<T>) {}

  /** Calls `callback` after each successful save. Returns a function that stops it. */
  onSaved(callback: (value: T) => void) {
    this.savedCallbacks.add(callback)
    return () => {
      this.savedCallbacks.delete(callback)
    }
  }

  change(value: T) {
    if (!this.saving) this.confirmed = this.options.read()
    this.options.write(value)
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
    this.confirmed = value
    // The saved document can replace what is on screen; show the waiting change again.
    if (this.waiting) this.options.write(this.waiting.value)
    this.savedCallbacks.forEach((callback) => callback(value))
  }

  private failed() {
    if (!this.waiting) this.options.write(this.confirmed)
    this.options.onError()
  }
}
