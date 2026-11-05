<template>
  <Button variant="ghost" size="md" icon="lucide-chevron-left" label="Back" @click="goUp" />
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import {
  isNavigationFailure,
  NavigationFailureType,
  useRouter,
  type RouteLocationRaw,
} from 'vue-router'

// A pop that goes nowhere fires no navigation, so this releases the wait.
const POP_TIMEOUT_MS = 700

const props = defineProps<{
  to: RouteLocationRaw
}>()

const router = useRouter()

// Unlike PageHeaderBackButton, this goes to the parent page wherever the user came from.
// It must not add a history entry, or the back gesture would return to the page just left.
async function goUp() {
  const parentPath = router.resolve(props.to).path
  const previous = router.options.history.state.back

  // Popping also keeps the parent's query, and avoids two entries for the same page.
  if (typeof previous === 'string' && router.resolve(previous).path === parentPath) {
    await pop()
    // `previous` is out of date if an earlier entry was replaced, and a pop can be cancelled.
    if (router.currentRoute.value.path === parentPath) return
  }

  // A page still loading rewrites its own query (CommentsArea drops ?comment=first_post),
  // which cancels this navigation if the parent's chunk has not arrived yet.
  const failure = await router.replace(props.to)
  if (isNavigationFailure(failure, NavigationFailureType.cancelled)) {
    await router.replace(props.to)
  }
}

function pop() {
  return new Promise<void>((resolve) => {
    const finish = () => {
      clearTimeout(timer)
      stopListening()
      resolve()
    }
    const timer = setTimeout(finish, POP_TIMEOUT_MS)
    const stopListening = router.afterEach(finish)
    router.back()
  })
}
</script>
