<template>
  <router-view v-slot="{ Component, route }">
    <PageHeader v-if="!route.meta.hideHeader">
      <div class="flex items-center space-x-1">
        <Breadcrumbs
          :items="[{ label: 'Spaces', route: { name: 'Spaces' } }, { label: space?.title }]"
        />
        <LucideLock v-if="space?.is_private" class="h-4 w-4 text-ink-gray-6" />
      </div>
      <SpaceOptions :spaceId="spaceId" />
    </PageHeader>
    <component class="flex-1" v-if="space" :is="Component" :space="space" />
  </router-view>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import SpaceOptions from '@/components/SpaceOptions.vue'
import LucideLock from '~icons/lucide/lock'
import { useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'

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
