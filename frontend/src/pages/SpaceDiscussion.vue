<template>
  <PageHeader>
    <Breadcrumbs
      :items="[
        { label: 'Spaces', route: { name: 'Spaces' } },
        {
          label: space?.title,
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
import { Breadcrumbs } from 'frappe-ui'
import DiscussionView from '@/components/DiscussionView.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDiscussion } from '@/data/discussions'
import { useSpace } from '@/data/spaces'

interface Props {
  spaceId: string
  postId: string
  slug?: string
}

const props = defineProps<Props>()
const space = useSpace(() => props.spaceId)
const discussion = useDiscussion(() => props.postId)
</script>
