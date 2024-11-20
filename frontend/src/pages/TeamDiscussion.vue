<template>
  <div class="flex" v-if="team.doc">
    <DiscussionView
      class="w-full"
      :postId="postId"
      :read-only-mode="Boolean(team.doc.archived_at) || $readOnlyMode"
    />
  </div>
</template>
<script setup lang="ts">
import { useTeam } from '@/data/teams'
import DiscussionView from '@/components/DiscussionView.vue'

const props = defineProps<{
  teamId: string
  postId: string
  slug: string
}>()

let team = useTeam(props.teamId)
</script>
