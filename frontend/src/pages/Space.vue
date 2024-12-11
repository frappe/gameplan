<template>
  <div>
    <PageHeader>
      <div class="flex items-center space-x-1">
        <Breadcrumbs
          :items="[{ label: 'Spaces', route: { name: 'Spaces' } }, { label: space.doc?.title }]"
        />
        <LucideLock v-if="space.doc?.is_private" class="h-4 w-4 text-ink-gray-6" />
      </div>
      <SpaceOptions :spaceId="spaceId" />
    </PageHeader>
    <router-view class="flex-1" v-if="space.doc" :space="space" :key="spaceId" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import { useProject } from '@/data/projects'
import SpaceOptions from '@/components/SpaceOptions.vue'
import LucideLock from '~icons/lucide/lock'

const props = defineProps<{
  spaceId: string
}>()

const spaceId = computed(() => props.spaceId)
const space = useProject(spaceId)

onMounted(() => {
  space.value.trackVisit.submit()
})
</script>
