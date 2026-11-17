<template>
  <div>
    <!-- A page with a parent keeps its phone header, so the up button still leads out. -->
    <PageHeaderMobile v-if="upTo" class="sm:hidden" :title="title">
      <template #prefix>
        <PageHeaderUpButton :to="upTo" />
      </template>
    </PageHeaderMobile>
    <PageHeader :class="{ 'hidden sm:flex': upTo }">
      <slot name="breadcrumbs">
        <Breadcrumbs :items="[{ label: 'Not found' }]" />
      </slot>
    </PageHeader>
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
import type { RouteLocationRaw } from 'vue-router'
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile, usePageMeta } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import PageHeaderUpButton from '@/components/PageHeaderUpButton.vue'
import { getHomeRoute } from '@/router'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    /** The parent page, for the up button in the phone header. */
    upTo?: RouteLocationRaw
  }>(),
  {
    title: 'Page not found',
    description: 'The link is invalid, or you no longer have access to this page.',
  },
)

defineSlots<{
  /** The trail to the missing page, ending in "Not found". Defaults to "Not found" alone. */
  breadcrumbs?: () => unknown
}>()

const homeRoute = computed(() => getHomeRoute())

usePageMeta(() => ({ title: props.title }))
</script>
