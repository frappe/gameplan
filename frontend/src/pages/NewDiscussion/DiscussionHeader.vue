<template>
  <PageHeaderMobile class="sm:hidden" :title="mobileTitle">
    <template #prefix>
      <PageHeaderBackButton :to="backRoute" />
    </template>
    <template #suffix>
      <div class="flex items-center gap-1">
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
        <Tooltip
          :text="isDraftLoading ? 'Draft is loading' : 'You cannot publish this draft'"
          :disabled="isComposerEditable"
        >
          <Button
            variant="solid"
            size="md"
            :loading="publishing"
            @click="publish"
            :disabled="!isComposerEditable"
          >
            Publish
          </Button>
        </Tooltip>
      </div>
    </template>
  </PageHeaderMobile>

  <PageHeader class="hidden sm:flex">
    <Breadcrumbs
      class="h-7"
      :items="[
        { label: 'Drafts', route: { name: 'Drafts' } },
        {
          label: isPersisted ? draftData.title : 'New Discussion',
          route: discussionRoute,
        },
      ]"
    />
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
      <Tooltip
        :text="isDraftLoading ? 'Draft is loading' : 'You cannot publish this draft'"
        :disabled="isComposerEditable"
      >
        <Button
          variant="solid"
          :loading="publishing"
          @click="publish"
          :disabled="!isComposerEditable"
        >
          Publish
        </Button>
      </Tooltip>
    </div>
  </PageHeader>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, type RouteLocationRaw } from 'vue-router'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  Button,
  Tooltip,
} from 'frappe-ui'
import { useNewDiscussionContext } from './useNewDiscussion'
import DiscussionSpaceSelector from './DiscussionSpaceSelector.vue'

const {
  isPersisted,
  draftData,
  sessionUser,
  author,
  isDraftLoading,
  isComposerEditable,
  deleteDraft,
  publish,
  publishing,
} = useNewDiscussionContext()

const route = useRoute()
const mobileTitle = computed(() => (isPersisted.value ? 'Draft' : 'New Discussion'))

// Cold-load fallback only: with any in-app history the back button walks it instead.
// A composer opened straight from a link belongs to a space, so send the user there.
// Drafts is the last resort, for a draft that has not picked a space yet.
const backRoute = computed<RouteLocationRaw>(() => {
  const communityId = routeParam(route.params.communityId)
  const spaceId = routeParam(route.query.spaceId) || draftData.value.project

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
