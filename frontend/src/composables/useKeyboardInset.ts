import { onScopeDispose, readonly, ref } from 'vue'

/**
 * Tracks how many CSS pixels the on-screen keyboard (or any bottom browser
 * chrome) currently covers, via the VisualViewport API.
 *
 * On mobile the layout viewport height doesn't change when the keyboard opens —
 * the browser just slides content up and shrinks the *visual* viewport. Reading
 * `window.visualViewport` lets us learn the covered height and dock UI (the
 * mobile comment toolbar) directly on top of the keyboard.
 *
 * `inset` is 0 when nothing covers the bottom (no keyboard, hardware keyboard,
 * or unsupported browser) and > 0 while the keyboard is open.
 */
export function useKeyboardInset() {
  const inset = ref(0)
  const vv = typeof window !== 'undefined' ? window.visualViewport : null

  function update() {
    if (!vv) return
    // Gap between the layout viewport bottom and the visible viewport bottom.
    const covered = window.innerHeight - (vv.height + vv.offsetTop)
    inset.value = Math.max(0, Math.round(covered))
  }

  if (vv) {
    vv.addEventListener('resize', update)
    vv.addEventListener('scroll', update)
    update()
    onScopeDispose(() => {
      vv.removeEventListener('resize', update)
      vv.removeEventListener('scroll', update)
    })
  }

  return { inset: readonly(inset) }
}
