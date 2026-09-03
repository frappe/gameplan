<template>
  <div class="pb-10">
    <header class="sticky top-0 z-10 border-b bg-surface-base px-4 py-2.5 sm:px-5">
      <div class="flex items-center justify-between">
        <Breadcrumbs :items="[{ label: 'Communities', route: { name: 'Teams' } }]" />
      </div>
    </header>
    <div class="divide-y px-4">
      <Links :links="activeCommunities" class="flex items-center py-3 font-medium text-ink-gray-8">
        <template v-slot="{ link: team }">
          <div class="flex w-full items-center">
            <CommunityImage :community="team" class="me-2 size-6 shrink-0 bg-surface-gray-1" />
            <span class="text-xl-medium">{{ team.title }}</span>
            <span v-if="team.is_private" class="lucide-lock ms-2 h-3 w-3" />
            <span class="lucide-chevron-right ms-auto h-5 w-5 text-ink-gray-5" />
          </div>
        </template>
      </Links>
    </div>
  </div>
</template>
<script setup>
import { Breadcrumbs } from 'frappe-ui'
import { activeCommunities } from '@/data/communities'
import CommunityImage from '@/components/CommunityImage.vue'
</script>
