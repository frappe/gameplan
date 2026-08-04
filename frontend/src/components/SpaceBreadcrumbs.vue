<template>
  <Breadcrumbs class="space-breadcrumbs" :items="breadcrumbItems">
    <template #prefix="{ item }">
      <component :is="item.prefix" v-if="item.prefix" class="mr-1.5 size-5 text-ink-gray-6" />
    </template>
    <template #suffix="{ item }">
      <span v-if="item.suffix" :class="[item.suffix, 'ml-1.5 size-3.5 text-ink-gray-6']" />
    </template>
  </Breadcrumbs>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import { useSpace } from '@/data/spaces'
import type { RouteLocationRaw } from 'vue-router'
import SpaceIcon from './SpaceIcon.vue'

const props = defineProps<{
  spaceId: string
  items?: {
    label: string
    route?: RouteLocationRaw
    suffix?: any
    prefix?: any
    onClick?: () => void
  }[]
}>()

const space = useSpace(() => props.spaceId)

// The community is named in the sidebar, one column to the left, so repeating it
// as the first crumb only costs horizontal room. The trail starts at the space.
const breadcrumbItems = computed(() => {
  return [
    {
      label: space.value?.title,
      prefix: h(SpaceIcon, { icon: space.value?.icon }),
      suffix: space.value?.is_private ? 'lucide-lock' : null,
      route: space.value
        ? { name: 'Space', params: { communityId: space.value.team, spaceId: space.value.name } }
        : undefined,
    },
    ...(props.items || []),
  ]
})
</script>

<style>
button:has(span.font-\[emoji\]) {
  align-items: baseline;
}
</style>
