<template>
  <div class="max-w-4xl mt-5 mx-auto px-2 sm:px-5" v-if="space.doc">
    <div class="flex px-3 mb-4 items-center justify-between">
      <SpaceTabs :spaceId="space.doc.name" />

      <Button
        variant="solid"
        :route="{ name: 'NewDiscussion', query: { spaceId: space.doc.name } }"
      >
        <template #prefix><LucidePlus class="h-4 w-4" /></template>
        Add new
      </Button>
    </div>
    <DiscussionList
      :listOptions="{ filters: { project: space.doc.name } }"
      routeName="ProjectDiscussion"
    />
  </div>
</template>
<script setup lang="ts">
import DiscussionList from '@/components/DiscussionList.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'

const props = defineProps<{
  space: Object
}>()
</script>
