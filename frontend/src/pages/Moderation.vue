<template>
  <PageHeaderMobile class="sm:hidden" title="Moderation">
    <template #prefix><PageHeaderBackButton :fallback-route="{ name: 'More' }" /></template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs :items="[{ label: 'Moderation', route: { name: 'Moderation' } }]" />
  </PageHeader>
  <div class="mx-auto w-full max-w-6xl px-4 py-6 text-ink-gray-9 sm:px-8">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <p class="text-base text-ink-gray-6">
        Review content and manage participation across your Communities.
      </p>
      <Select
        v-if="options.length && !siteWide"
        v-model="selected"
        label="Community"
        class="w-full sm:w-64"
        :options="options"
      />
    </div>
    <div v-if="isGlobalAdmin(useSessionUser())" class="mb-5 flex gap-2">
      <Button :variant="siteWide ? 'subtle' : 'solid'" @click="setView(false)"
        >Community moderation</Button
      ><Button :variant="siteWide ? 'solid' : 'subtle'" @click="setView(true)"
        >Account suspensions</Button
      >
    </div>
    <AccountSuspensions v-if="siteWide" />
    <CommunityModeration v-else-if="selected" :key="selected" :community-id="selected" />
    <p v-else class="py-12 text-center text-base text-ink-gray-6">
      Only Community moderators can open this page.
    </p>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Breadcrumbs,
  PageHeader,
  PageHeaderBackButton,
  PageHeaderMobile,
  Button,
  Select,
} from 'frappe-ui'
import { communities } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canModerateCommunity, isGlobalAdmin } from '@/utils/permissions'
import CommunityModeration from './CommunityModeration.vue'
import AccountSuspensions from '@/components/AccountSuspensions.vue'
const route = useRoute()
const router = useRouter()
const siteWide = computed(() => route.query.scope === 'site' && isGlobalAdmin(useSessionUser()))
function setView(site: boolean) {
  router.replace({ name: 'Moderation', query: site ? { scope: 'site' } : {} })
}
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
