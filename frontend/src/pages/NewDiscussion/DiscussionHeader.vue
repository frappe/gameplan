<template>
  <PageHeaderMobile class="sm:hidden">
    <template #prefix>
      <PageHeaderBackButton :to="backRoute" />
    </template>
    <!-- The header centres the title inside the width the widest control leaves it. The
         split Publish button is wide, so the controls shrink a size and the title steps
         down from the header's default text-xl so "New Discussion" fits on a phone. -->
    <span class="text-lg-semibold">{{ mobileTitle }}</span>
    <template #suffix>
      <div class="flex items-center gap-1">
        <button
          v-if="sessionUser.name == author.name"
          type="button"
          class="inline-flex size-7 shrink-0 items-center justify-center rounded-4 text-ink-gray-7 transition hover:bg-surface-gray-2 active:bg-surface-gray-3 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Delete draft"
          title="Delete draft"
          :disabled="isDraftLoading"
          @click.prevent.stop="deleteDraft"
        >
          <span class="lucide-trash-2 size-4" aria-hidden="true" />
        </button>
        <PublishControls size="sm" />
      </div>
    </template>
  </PageHeaderMobile>

  <PageHeader class="hidden sm:flex">
    <div class="flex min-w-0 items-center gap-2">
      <Breadcrumbs
        class="h-7"
        :items="[
          { label: 'Drafts', route: { name: 'Drafts' } },
          {
            label: isPersisted ? draftData?.title : 'New Discussion',
            route: discussionRoute,
          },
        ]"
      />
      <!-- Status sits with the name, away from the actions, so the right-hand controls
           keep a fixed width whether or not the draft is scheduled. -->
      <Badge v-if="scheduledAt" :title="`Scheduled for ${scheduledAtLabel}`">
        <template #prefix>
          <span class="lucide-calendar-clock size-3.5" aria-hidden="true" />
        </template>
        {{ scheduledAtLabel }}
      </Badge>
    </div>
    <div class="flex shrink-0 items-center space-x-2">
      <DiscussionSpaceSelector />

      <button
        v-if="sessionUser.name == author.name"
        type="button"
        class="inline-flex size-8 shrink-0 items-center justify-center rounded-4 text-ink-gray-7 transition hover:bg-surface-gray-2 active:bg-surface-gray-3 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="Delete draft"
        title="Delete draft"
        :disabled="isDraftLoading"
        @click.prevent.stop="deleteDraft"
      >
        <span class="lucide-trash-2 size-4" aria-hidden="true" />
      </button>
      <PublishControls />
    </div>
  </PageHeader>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, type RouteLocationRaw } from 'vue-router'
import { PageHeaderBackButton, PageHeaderMobile, PageHeader, Breadcrumbs, Badge } from 'frappe-ui'
import { useNewDiscussionContext } from './useNewDiscussion'
import DiscussionSpaceSelector from './DiscussionSpaceSelector.vue'
import PublishControls from './PublishControls.vue'

const {
  isPersisted,
  draftData,
  sessionUser,
  author,
  isDraftLoading,
  deleteDraft,
  scheduledAt,
  scheduledAtLabel,
} = useNewDiscussionContext()

const route = useRoute()
const mobileTitle = computed(() => (isPersisted.value ? 'Draft' : 'New Discussion'))

// Cold-load fallback only: with any in-app history the back button walks it instead.
// A composer opened straight from a link belongs to a space, so send the user there.
// Drafts is the last resort, for a draft that has not picked a space yet.
const backRoute = computed<RouteLocationRaw>(() => {
  const communityId = routeParam(route.params.communityId)
  const spaceId = routeParam(route.query.spaceId) || draftData.value?.project

  if (communityId && spaceId) {
    return { name: 'SpaceDiscussions', params: { communityId, spaceId } }
  }
  if (communityId) {
    return { name: 'Discussions', params: { communityId } }
  }
  return { name: 'Drafts' }
})

function routeParam(value: unknown): string | undefined {
  const resolved = Array.isArray(value) ? value[0] : value
  return typeof resolved === 'string' && resolved ? resolved : undefined
}

const discussionRoute = computed(() => {
  if (!route.params.communityId) {
    return { name: 'LegacyNewDiscussion' }
  }

  return {
    name: 'NewDiscussion',
    params: { communityId: route.params.communityId },
  }
})
</script>
