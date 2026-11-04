import { computed, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { useEventListener, useIntervalFn } from '@vueuse/core'
import { call } from 'frappe-ui'

export const slowModeIntervals = [
  { value: '0', label: 'Off' },
  { value: '30', label: '30 seconds' },
  { value: '60', label: '1 minute' },
  { value: '300', label: '5 minutes' },
  { value: '900', label: '15 minutes' },
  { value: '3600', label: '1 hour' },
  { value: '86400', label: '1 day' },
]
export const slowModeLabel = (seconds = 0) =>
  slowModeIntervals.find((option) => Number(option.value) === seconds)?.label ||
  `${seconds} seconds`
export type SlowModeStatus = {
  seconds: number
  can_manage: boolean
  exempt: boolean
  retry_after: number
}
const changes = ref(0)
export const notifySlowModeChanged = () => changes.value++

export function useSlowMode(discussion: MaybeRefOrGetter<string | undefined>) {
  const data = ref<SlowModeStatus | null>(null)
  const now = ref(Date.now())
  const deadline = ref(0)
  let request = 0
  async function refresh() {
    const name = toValue(discussion)
    const current = ++request
    if (!name) {
      data.value = null
      deadline.value = 0
      return
    }
    try {
      const result = await call<SlowModeStatus>('gameplan.slow_mode.status', { discussion: name })
      if (current !== request) return
      data.value = result
      now.value = Date.now()
      deadline.value = now.value + result.retry_after * 1000
    } catch {
      // Submission always rechecks the current policy and access on the server.
    }
  }
  watch([() => toValue(discussion), changes], refresh, { immediate: true })
  useEventListener(window, 'focus', refresh)
  useIntervalFn(() => (now.value = Date.now()), 1000)
  const remaining = computed(() => Math.max(0, Math.ceil((deadline.value - now.value) / 1000)))
  return { data, remaining, refresh }
}
