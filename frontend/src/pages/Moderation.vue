<template>
  <PageHeaderMobile class="sm:hidden" :title="headerTitle">
    <template #prefix><PageHeaderBackButton :fallback-route="{ name: 'More' }" /></template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs :items="[{ label: headerTitle }]" />
  </PageHeader>
  <div class="flex min-h-0 flex-1 flex-col text-ink-gray-9">
    <CommunityModeration
      v-if="selected"
      :key="selected"
      :community-id="selected"
      @section-title="sectionTitle = $event"
    >
      <template #sidebar>
        <Select v-model="selected" label="Community" :options="options" />
      </template>
    </CommunityModeration>
    <p v-else class="py-12 text-center text-base text-ink-gray-6">
      Only Community moderators can open this page.
    </p>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Breadcrumbs, PageHeader, PageHeaderBackButton, PageHeaderMobile, Select } from 'frappe-ui'
import { communities } from '@/data/communities'
import { useSessionUser } from '@/data/users'
import { canModerateCommunity } from '@/utils/permissions'
import CommunityModeration from './CommunityModeration.vue'
const route = useRoute()
const router = useRouter()
const sectionTitle = ref('Removed content')
const headerTitle = computed(() => (selected.value ? sectionTitle.value : 'Moderation'))
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
