<template>
  <router-view v-slot="{ Component, route }">
    <MobileHeader v-if="!route.meta.hideHeader" class="sm:hidden" :title="space?.title || 'Space'">
      <button
        type="button"
        class="inline-flex max-w-full items-center gap-1 transition active:opacity-60"
        @click="menuOpen = true"
      >
        <MobileHeaderTitle :title="space?.title || 'Space'">
          <template #icon>
            <SpaceIcon :icon="space?.icon" class="size-5 text-ink-gray-6" />
          </template>
        </MobileHeaderTitle>
        <span class="size-4 shrink-0 text-ink-gray-5 lucide-chevron-down" aria-hidden="true" />
      </button>
      <template #left>
        <MobileBackButton
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
    </MobileHeader>
    <BottomSheet v-model="menuOpen" :title="community?.title || 'Community'">
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
import { useRouter } from 'vue-router'
import { Button, useDoctype } from 'frappe-ui'
import SpaceHeaderActionsTarget from '@/components/SpaceHeaderActionsTarget.vue'
import { useSpace, spaces as spaceList } from '@/data/spaces'
import { GPProject } from '@/types/doctypes'
import BottomSheet from '@/components/BottomSheet.vue'
import CommunityMenu from '@/components/CommunityMenu.vue'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import MobileBackButton from '@/components/MobileBackButton.vue'
import MobileHeader from '@/components/MobileHeader.vue'
import MobileHeaderTitle from '@/components/MobileHeaderTitle.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { useCommunity } from '@/data/communities'
import { readOnlyMode } from '@/data/readOnlyMode'
import { session } from '@/data/session'

const props = defineProps<{
  communityId: string
  spaceId: string
}>()

const router = useRouter()
const community = useCommunity(() => props.communityId)
const menuOpen = ref(false)
const spaces = useDoctype<GPProject>('GP Project')
const space = useSpace(() => props.spaceId)
const canEditSpace = computed(
  () => session.isAuthenticated && !readOnlyMode && !space.value?.archived_at,
)

// A space can only be reached under the community that owns it. If the URL carries a stale
// community (e.g. after a move), heal it to the canonical route instead of rendering a mismatch.
watch(
  space,
  (resolved) => {
    if (resolved?.team && resolved.team !== props.communityId) {
      router.replace({
        name: 'Space',
        params: { communityId: resolved.team, spaceId: props.spaceId },
      })
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (session.canBrowsePublicWeb) return

  spaces.runDocMethod.submit({
    method: 'track_visit',
    name: props.spaceId,
  })
})
</script>
