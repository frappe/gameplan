<template>
  <router-view v-slot="{ Component, route }">
    <PageHeader v-if="!route.meta.hideHeader">
      <div class="flex items-center space-x-1">
        <SpaceBreadcrumbs :spaceId="spaceId" />
      </div>
      <SpaceOptions :spaceId="spaceId" placement="right" />
    </PageHeader>
    <component class="flex-1" v-if="space" :is="Component" :space="space" />
    <div class="p-5 max-w-4xl mx-auto" v-if="spaceList.isFinished && !space">
      <EmptyStateBox>
        <div class="text-ink-gray-6">Page not found</div>
      </EmptyStateBox>
    </div>
  </router-view>
</template>
<script setup lang="ts">
import { onMounted, h } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import SpaceOptions from '@/components/SpaceOptions.vue'
import LucideLock from '~icons/lucide/lock'
import { useSpace, spaces as spaceList } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'

const props = defineProps<{
  spaceId: string
}>()

const spaces = useDoctype<GPProject>('GP Project')
const space = useSpace(() => props.spaceId)

onMounted(() => {
  spaces.runDocMethod.submit({
    method: 'track_visit',
    name: props.spaceId,
  })
})
</script>
