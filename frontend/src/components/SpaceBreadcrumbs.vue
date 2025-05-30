<template>
  <Breadcrumbs
    class="space-breadcrumbs"
    :items="[
      {
        label: category?.title || 'Spaces',
        route: { name: 'Spaces', query: category ? { teamId: category.name } : undefined },
      },
      {
        label: space?.title,
        prefix: h('span', { class: 'grid place-items-center font-[emoji] text-lg' }, space?.icon),
        suffix: space?.is_private ? LucideLock : null,
        route: { name: 'Space', params: { spaceId } },
      },
      ...(items || []),
    ]"
  >
    <template #prefix="{ item }">
      <component :is="item.prefix" v-if="item.prefix" class="mr-1.5 size-4 text-ink-gray-6" />
    </template>
    <template #suffix="{ item }">
      <component :is="item.suffix" v-if="item.suffix" class="ml-1.5 size-3.5 text-ink-gray-6" />
    </template>
  </Breadcrumbs>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import { useSpace } from '@/data/spaces'
import LucideLock from '~icons/lucide/lock'
import { RouteComponent } from 'vue-router'
import { useTeam } from '@/data/teams'

const props = defineProps<{
  spaceId: string
  items?: {
    label: string
    route?: RouteComponent
    suffix?: any
    prefix?: any
    onClick?: () => void
  }[]
}>()

const space = useSpace(() => props.spaceId)
const category = useTeam(() => space.value?.team)
</script>

<style>
button:has(span.font-\[emoji\]) {
  align-items: baseline;
}
</style>
