<template>
  <!-- <div>{{ spaceId }}</div> -->
  <PageHeader>
    <Breadcrumbs :items="[{ label: 'Spaces' }, { label: space.doc?.title }]" />
  </PageHeader>
  <router-view class="flex-1" v-if="space.doc" :space="space" />
</template>
<script setup lang="ts">
import { createDocumentResource, Breadcrumbs } from 'frappe-ui'

const props = defineProps<{
  spaceId: string
}>()

const space = createDocumentResource({
  doctype: 'GP Project',
  name: props.spaceId,
  whitelistedMethods: {
    moveToTeam: 'move_to_team',
    mergeWithProject: 'merge_with_project',
    archive: 'archive',
    unarchive: 'unarchive',
    inviteMembers: 'invite_members',
    inviteGuest: 'invite_guest',
    removeGuest: 'remove_guest',
    trackVisit: 'track_visit',
    follow: 'follow',
    unfollow: 'unfollow',
  },
  onSuccess() {
    space.trackVisit.submit()
  },
})
</script>
