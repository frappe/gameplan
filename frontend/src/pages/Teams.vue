<template>
  <div class="pb-10">
    <header class="sticky top-0 z-10 border-b bg-surface-base px-4 py-2.5 sm:px-5">
      <div class="flex items-center justify-between">
        <Breadcrumbs :items="[{ label: 'Communities', route: { name: 'Teams' } }]" />
      </div>
    </header>
    <div class="divide-y px-4">
      <RouterLink
        v-for="team in activeCommunities"
        :key="team.name"
        :to="{ name: 'Discussions', params: { communityId: team.name } }"
        class="flex items-center py-3 font-medium text-ink-gray-8"
      >
        <div class="flex w-full items-center">
          <CommunityImage :community="team" class="mr-2 size-6 shrink-0 bg-surface-gray-1" />
          <span class="text-lg-medium">{{ team.title }}</span>
          <span v-if="isMemberAccess(team.visibility)" class="lucide-lock ml-2 h-3 w-3" />
          <span class="lucide-chevron-right ml-auto h-5 w-5 text-ink-gray-5" />
        </div>
      </RouterLink>
    </div>
    <nav v-if="isAnonymousVisitor()" aria-label="Pagination" class="flex gap-3 px-4 py-3">
      <a v-if="publicPageStart() > 0" :href="publicPageLink(-1)" class="underline">Previous page</a>
      <a
        v-if="availableCommunities.length > publicPageStart() + PUBLIC_PAGE_SIZE"
        :href="publicPageLink(1)"
        class="underline"
        >Next page</a
      >
    </nav>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import { Breadcrumbs } from 'frappe-ui'
import { activeCommunities as joinedCommunities, availableCommunities } from '@/data/communities'
import CommunityImage from '@/components/CommunityImage.vue'
import { isMemberAccess } from '@/utils/visibility'
import {
  isAnonymousVisitor,
  publicPageStart,
  publicPageLink,
  PUBLIC_PAGE_SIZE,
} from '@/utils/publicAccess'

const activeCommunities = computed(() =>
  isAnonymousVisitor()
    ? availableCommunities.value.slice(publicPageStart(), publicPageStart() + PUBLIC_PAGE_SIZE)
    : joinedCommunities.value,
)
</script>
