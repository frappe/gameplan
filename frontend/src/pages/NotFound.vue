<template>
  <div>
    <slot name="header" />
    <div class="body-container py-8">
      <EmptyStateBox icon="lucide-link-2-off" :title="title" :description="description">
        <Button class="mt-4" variant="subtle" label="Go to Home" :route="homeRoute" />
      </EmptyStateBox>
    </div>
  </div>
</template>

<script setup lang="ts">
// The /404 route, and the in-place state for a space, discussion or profile that is
// missing or out of reach. Rendered inside the app shell, so the sidebar stays.
import { computed } from 'vue'
import { Button, usePageMeta } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import { getHomeRoute } from '@/router'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
  }>(),
  {
    title: 'Page not found',
    description: 'The link is invalid, or you no longer have access to this page.',
  },
)

defineSlots<{
  /** A PageHeader with breadcrumbs, for pages that keep their place in the app. */
  header?: () => unknown
}>()

const homeRoute = computed(() => getHomeRoute())

usePageMeta(() => ({ title: props.title }))
</script>
