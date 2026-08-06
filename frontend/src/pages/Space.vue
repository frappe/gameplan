<template>
  <router-view v-slot="{ Component, route }">
    <PageHeaderMobile
      v-if="!route.meta.hideHeader"
      class="sm:hidden"
      :title="space?.title || 'Space'"
    >
      <button
        type="button"
        class="inline-flex max-w-full items-center gap-1 transition active:opacity-60"
        @click="menuOpen = true"
      >
        <PageHeaderMobileTitle :title="space?.title || 'Space'">
          <template #icon>
            <SpaceIcon :icon="space?.icon" class="size-5 text-ink-gray-6" />
          </template>
        </PageHeaderMobileTitle>
        <span class="size-4 shrink-0 text-ink-gray-5 lucide-chevron-down" aria-hidden="true" />
      </button>
      <template #left>
        <PageHeaderBackButton
          :to="{ name: 'Discussions', params: { communityId } }"
          label="All discussions"
        />
      </template>
      <template #right>
        <Button
          v-if="route.name === 'SpaceDiscussions' && canEditSpace"
          variant="ghost"
          size="md"
          icon="lucide-plus"
          label="New discussion"
          :route="{
            name: 'NewDiscussion',
            params: { communityId },
            query: { spaceId },
          }"
        />
      </template>
    </PageHeaderMobile>
    <BottomSheet v-model:open="menuOpen" :title="community?.title || 'Community'">
      <CommunityMenu
        class="pb-6"
        :communityId="communityId"
        :activeSpaceId="spaceId"
        @navigate="menuOpen = false"
      />
    </BottomSheet>
    <PageHeader v-if="!route.meta.hideHeader" class="hidden sm:flex">
      <div class="flex w-full items-center justify-between gap-3">
        <div class="flex min-w-0 items-center gap-2">
          <SpaceBreadcrumbs :spaceId="spaceId" />
          <SpaceHeaderActionsTarget placement="title" class="shrink-0" />
          <Badge v-if="space?.archived_at">Archived</Badge>
        </div>
        <SpaceHeaderActionsTarget />
      </div>
    </PageHeader>
    <component class="flex-1" v-if="space" :is="Component" :space="space" />
    <div class="body-container pt-5" v-if="spaceList.isFinished && !space">
      <EmptyStateBox>
        <div class="text-ink-gray-6">Page not found</div>
      </EmptyStateBox>
    </div>
  </router-view>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BottomSheet,
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeaderMobileTitle,
  PageHeader,
  Button,
} from 'frappe-ui'
import SpaceHeaderActionsTarget from '@/components/SpaceHeaderActionsTarget.vue'
import { useSpace, spaces as spaceList, trackSpaceVisit } from '@/data/spaces'
import CommunityMenu from '@/components/CommunityMenu.vue'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { useCommunity } from '@/data/communities'
import { readOnlyMode } from '@/data/readOnlyMode'
import { useOwnedRouteWrites } from '@/composables/useOwnedRouteWrites'

const props = defineProps<{
  communityId: string
  spaceId: string
}>()

const router = useRouter()
// Named apart from the slot-scoped `route` in the template above: that one is the route
// this page is rendering, this one is the URL the browser is actually on.
const currentRoute = useRoute()
const community = useCommunity(() => props.communityId)
const menuOpen = ref(false)
const space = useSpace(() => props.spaceId)
const canEditSpace = computed(() => !readOnlyMode && !space.value?.archived_at)

// This page also renders behind the settings overlay, where the URL belongs to /settings/*
// and healing it from here would navigate the app off the settings route, closing the dialog.
// Wait for the URL to be ours again instead — the mismatch is still worth correcting then.
const runWhenOwned = useOwnedRouteWrites(
  () => routeParam(currentRoute.params.spaceId) === props.spaceId,
)

// A space can only be reached under the community that owns it. If the URL carries a stale
// community (e.g. after a move), heal it to the canonical route instead of rendering a mismatch.
// Reads its state when it runs, not when it was queued, so a deferred heal can't pair the
// community of the space we started on with the space the URL ended up on.
function healStaleCommunityInUrl() {
  const canonicalCommunityId = space.value?.team
  if (!canonicalCommunityId || canonicalCommunityId === props.communityId) return
  router.replace({
    name: 'Space',
    params: { communityId: canonicalCommunityId, spaceId: props.spaceId },
  })
}

watch(space, () => runWhenOwned(healStaleCommunityInUrl), { immediate: true })

function routeParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value
}

onMounted(() => {
  trackSpaceVisit(props.spaceId)
})
</script>
