<template>
  <PageHeader>
    <Breadcrumbs
      :items="[
        { label: 'Spaces', route: { name: 'Spaces' } },
        {
          label: space.title,
          route: { name: 'SpaceDiscussions', params: { spaceId } },
        },
        { label: discussion?.doc?.title },
      ]"
    />
  </PageHeader>
  <div class="flex" v-if="space">
    <DiscussionView
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(space?.archived_at) || $readOnlyMode"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Breadcrumbs, getCachedDocumentResource } from 'frappe-ui'
import { getProject } from '@/data/projects'
import DiscussionView from '@/components/DiscussionView.vue'
import PageHeader from '@/components/PageHeader.vue'

interface Props {
  spaceId: string | number
  postId: string | number
  slug?: string
}

const props = defineProps<Props>()
const space = computed(() => getProject(props.spaceId))
const discussion = computed(() => getCachedDocumentResource('GP Discussion', props.postId))
</script>
