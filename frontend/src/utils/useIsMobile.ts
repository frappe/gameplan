import { useMediaQuery } from '@vueuse/core'
import type { Ref } from 'vue'

/** Viewport below Tailwind's `sm` breakpoint (640px). */
const MOBILE_QUERY = '(max-width: 639.98px)'

/**
 * Whether the viewport is narrower than Tailwind's `sm` breakpoint, which is
 * where the app swaps between the mobile and desktop layouts.
 *
 * Local because frappe-ui stopped exporting `useIsMobile`/`useScreenSize` in
 * 1.0.0. A media query beats a resize listener here: the browser evaluates it
 * and only notifies on a breakpoint crossing, so a drag-resize does not wake
 * every consumer on each frame.
 */
export function useIsMobile(): Ref<boolean> {
  return useMediaQuery(MOBILE_QUERY)
}
