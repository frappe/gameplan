import { computed, shallowRef } from 'vue'
import { useRoute, type RouteLocationNormalized } from 'vue-router'

/**
 * The route a navigation is heading to, from the moment it starts until it lands.
 * A switch can wait on page code or a guard, and the router only updates the current
 * route at the end. Set by the router's guards.
 */
export const navigationTarget = shallowRef<RouteLocationNormalized | null>(null)

/**
 * The route that navigation (the rail, the sidebar, the tab bar) should mark as active.
 * It follows a click at once, so the clicked item lights up before the page arrives.
 */
export function useActiveNavRoute() {
  const route = useRoute()
  return computed(() => navigationTarget.value ?? route)
}
