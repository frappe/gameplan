<template>
  <div class="pb-10">
    <header class="sticky top-0 z-10 border-b bg-surface-white px-4 py-2.5 sm:px-5">
      <div class="flex items-center justify-between">
        <Breadcrumbs :items="[{ label: 'Teams', route: { name: 'Teams' } }]" />
      </div>
    </header>
    <div class="divide-y px-4">
      <Links :links="activeTeams" class="flex items-center py-3 font-medium text-ink-gray-8">
        <template v-slot="{ link: team }">
          <div class="flex w-full items-center">
            <span class="mr-2 flex h-5 w-5 items-center justify-center text-xl">
              {{ team.icon }}
            </span>
            <span class="text-lg font-medium">{{ team.title }}</span>
            <LucideLock v-if="team.is_private" class="ml-2 h-3 w-3" />
            <LucideChevronRight class="ml-auto h-5 w-5 text-ink-gray-5" />
          </div>
        </template>
      </Links>
    </div>
  </div>
</template>
<script setup>
import { Breadcrumbs } from 'frappe-ui'
import { activeTeams } from '@/data/teams'
</script>
