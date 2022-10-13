<template>
  <div class="py-6">
    <h1 class="mb-6 text-2xl font-semibold">Teams</h1>
    <div class="divide-y">
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
import { computed } from 'vue'
import Links from '@/components/Links.vue'
import { teams } from '@/data/teams'

let activeTeams = computed(() => teams.data.filter((team) => !team.archived_at))
</script>
