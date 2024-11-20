<template>
  <div class="pb-10">
    <header class="sticky top-0 z-10 border-b bg-white px-4 py-2.5 sm:px-5">
      <div class="flex items-center justify-between">
        <Breadcrumbs :items="[{ label: 'Teams', route: { name: 'Teams' } }]" />
      </div>
    </header>
    <div class="mx-auto max-w-3xl sm:px-5 sm:pt-6">
      <div>
        <router-link
          :to="{ name: 'Team', params: { teamId: d.name } }"
          v-for="(d, index) in activeTeams"
          :key="d.name"
          class="group relative block rounded-[10px] transition hover:bg-gray-100"
        >
          <div class="flex items-start px-3 py-2">
            <div class="mr-1 grid h-5 w-5 place-content-center">
              <span class="font-[emoji]">{{ d.icon }}</span>
            </div>
            <div>
              <div
                class="flex items-center overflow-hidden text-ellipsis whitespace-nowrap leading-none text-gray-900"
              >
                <span
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium leading-5"
                >
                  {{ d.title }}
                </span>
              </div>
              <div class="mt-1.5 flex min-w-0 items-center justify-between">
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-base text-gray-600"
                >
                  <span>
                    {{ d.members.length == 1 ? '1 member' : `${d.members.length} members` }}
                  </span>
                </div>
              </div>
            </div>
            <div class="ml-auto self-center">
              <Button class="w-15" v-if="!d.hasJoined">Join</Button>
              <Button class="w-15" v-else>Leave</Button>
            </div>
          </div>
          <div
            class="mx-3 h-px border-t border-gray-200"
            v-if="index < activeTeams.length - 1"
          ></div>
        </router-link>
        <!-- <Links :links="activeTeams" class="flex items-center py-3 font-medium text-gray-900">
          <template v-slot="{ link: team }">
            <div class="flex w-full items-center">
              <span class="mr-2 flex h-5 w-5 items-center justify-center text-xl">
                {{ team.icon }}
              </span>
              <span class="text-lg font-medium">{{ team.title }}</span>
              <LucideLock v-if="team.is_private" class="ml-2 h-3 w-3" />
              <LucideChevronRight class="ml-auto h-5 w-5 text-gray-600" />
            </div>
          </template>
        </Links> -->
      </div>
    </div>
  </div>
</template>
<script setup>
import { Breadcrumbs } from 'frappe-ui'
import { activeTeams } from '@/data/teams'
</script>
