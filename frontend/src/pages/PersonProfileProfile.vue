<template>
  <div class="pb-16">
    <!-- Mirrors the rendered layout: one column below `sm`, four above. -->
    <div v-if="!bentoCardsLoaded" class="grid grid-cols-1 gap-3 sm:grid-cols-4">
      <Skeleton class="aspect-[4/1] rounded-xl sm:col-span-4" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-square rounded-xl sm:col-span-1" />
      <Skeleton class="aspect-[2/1] rounded-xl sm:col-span-2" />
    </div>
    <ProfileBentoGrid v-else :cards="bentoCards" />
  </div>
</template>

<script setup lang="ts">
import { Skeleton } from 'frappe-ui'
import ProfileBentoGrid from '@/components/ProfileBento/ProfileBentoGrid.vue'
import type { ProfileBentoCard } from '@/components/ProfileBento/types'
import type { GPUserProfile } from '@/types/doctypes'

defineOptions({
  name: 'PersonProfileProfile',
})

// `profile` is passed by PersonProfile's router-view. Declaring it keeps it out
// of `$attrs`, where an object prop would land on the root element as an attribute.
defineProps<{
  profile: { doc?: GPUserProfile | null }
  bentoCards: ProfileBentoCard[]
  bentoCardsLoaded: boolean
  isOwnProfile: boolean
}>()
</script>
