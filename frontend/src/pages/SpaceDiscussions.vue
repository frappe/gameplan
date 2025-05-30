<template>
  <div class="max-w-4xl mt-5 mx-auto px-2 sm:px-5">
    <div class="flex px-3 mb-4 items-center justify-between">
      <SpaceTabs :spaceId="spaceId" />
      <Button variant="solid" :route="{ name: 'NewDiscussion', query: { spaceId: spaceId } }">
        <template #prefix><LucidePlus class="h-4 w-4" /></template>
        Add new
      </Button>
    </div>
    <DiscussionList
      :filters="() => ({ project: spaceId })"
      :cacheKey="`SpaceDiscussions-${spaceId}`"
    />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'

defineProps<{
  spaceId: string
}>()
</script>
