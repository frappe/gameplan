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

const props = defineProps<{
  to: RouteLocationRaw
}>()

const router = useRouter()

// Unlike PageHeaderBackButton, this goes to the parent page wherever the user came from.
// It must not add a history entry, or the back gesture would return to the page just left.
async function goUp() {
  const previous = router.options.history.state.back
  const isParentPrevious =
    typeof previous === 'string' && router.resolve(previous).path === router.resolve(props.to).path

  // Popping also keeps the parent's query, and avoids two entries for the same page.
  if (isParentPrevious) {
    router.back()
    return
  }

  // A page still loading rewrites its own query (CommentsArea drops ?comment=first_post),
  // which cancels this navigation if the parent's chunk has not arrived yet.
  const failure = await router.replace(props.to)
  if (isNavigationFailure(failure, NavigationFailureType.cancelled)) {
    await router.replace(props.to)
  }
}
</script>
