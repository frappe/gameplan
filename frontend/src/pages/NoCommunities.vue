<template>
  <div class="body-container py-8">
    <EmptyStateBox class="mx-auto max-w-2xl px-6">
      <LucideFolderX class="mb-3 size-7 text-ink-gray-4" />
      <div class="text-base text-ink-gray-7">
        {{ hasCommunityToJoin ? 'You have not joined a community' : 'No communities available' }}
      </div>
      <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">
        {{ description }}
      </p>
      <Button
        v-if="hasCommunityToJoin || canManageCommunities"
        class="mt-4"
        variant="solid"
        icon-left="lucide-building-2"
        @click="showCommunitiesSettings()"
      >
        {{ canManageCommunities ? 'Manage communities' : 'Browse communities' }}
      </Button>
    </EmptyStateBox>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, usePageMeta } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import { useCanManageCommunities } from '@/composables/useCanManageCommunities'
import { showCommunitiesSettings } from '@/components/Settings'
import { availableCommunities } from '@/data/communities'
import { useSessionUser } from '@/data/users'

const sessionUser = useSessionUser()
const canManageCommunities = useCanManageCommunities()

// This page is only reached with no community joined, so any public community the
// user can see is one they can join from the Communities settings tab.
const hasCommunityToJoin = computed(
  () =>
    !sessionUser.isGuest && availableCommunities.value.some((community) => !community.is_private),
)

const description = computed(() => {
  if (hasCommunityToJoin.value) {
    return 'Join a community to see its spaces and discussions in your sidebar.'
  }
  return canManageCommunities.value
    ? 'Create or unarchive a community so your team can start collaborating.'
    : 'Ask a Gameplan Admin to create or unarchive a community so you can start collaborating.'
})

usePageMeta(() => {
  return {
    title: 'No communities available',
  }
})
</script>
