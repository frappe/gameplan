<template>
  <div class="mx-auto w-full max-w-6xl px-4 py-6 text-ink-gray-9 sm:px-8">
    <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-2">
        <h1 class="text-2xl-semibold">Moderation</h1>
        <p class="text-base text-ink-gray-6">
          Review content and manage participation across your Communities.
        </p>
      </div>
      <Select
        v-if="options.length"
        v-model="selected"
        label="Community"
        class="w-full sm:w-64"
        :options="options"
      />
    </header>
    <CommunityModeration v-if="selected" :key="selected" :community-id="selected" />
    <p v-else class="py-12 text-center text-base text-ink-gray-6">
      Only Community moderators can open this page.
    </p>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Select } from 'frappe-ui'
import { communities } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canModerateCommunity } from '@/utils/permissions'
import CommunityModeration from './CommunityModeration.vue'
const route = useRoute()
const router = useRouter()
const options = computed(() =>
  (communities.data || [])
    .filter((community) => canModerateCommunity(community, useSessionUser()))
    .map((community) => ({ label: community.title, value: community.name })),
)
const selected = computed({
  get: () =>
    options.value.find((option) => option.value === route.query.community)?.value ||
    options.value[0]?.value ||
    '',
  set: (community) => router.replace({ name: 'Moderation', query: { community } }),
})
</script>
