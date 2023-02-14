<template>
  <div class="pb-10">
    <div class="sticky top-0 border-b bg-white px-4 py-3">
      <h1 class="text-2xl font-semibold">Teams</h1>
    </div>
    <div class="divide-y px-4">
      <Links
        :links="activeTeams"
        class="flex items-center py-4 font-medium text-gray-900"
      >
        <template v-slot="{ link: team }">
          <div class="flex w-full items-center">
            <span class="mr-2 flex h-5 w-5 items-center justify-center text-xl">
              {{ team.icon }}
            </span>
            <span class="text-xl">{{ team.title }}</span>
            <FeatherIcon
              v-if="team.is_private"
              name="lock"
              class="ml-2 h-3 w-3"
            />
            <FeatherIcon
              name="chevron-right"
              class="ml-auto h-5 w-5 text-gray-600"
            />
          </div>
        </template>
      </Links>
    </div>
  </div>
</template>
<script setup>
import Links from '@/components/Links.vue'
import { activeTeams } from '@/data/teams'
</script>
