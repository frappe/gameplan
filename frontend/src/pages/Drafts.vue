<template>
  <PageHeaderMobile class="sm:hidden" title="Drafts">
    <template #prefix>
      <Button v-if="isBulkDeleteMode" variant="ghost" size="md" @click="cancelBulkDelete">
        Cancel
      </Button>
      <PageHeaderBackButton v-else :to="{ name: 'More' }" />
    </template>
    <template #suffix>
      <div class="flex items-center gap-2">
        <template v-if="!isBulkDeleteMode">
          <Button
            v-show="drafts.data?.length"
            variant="ghost"
            size="md"
            @click="isBulkDeleteMode = true"
          >
            Select
          </Button>
          <Button
            v-if="!readOnlyMode"
            variant="subtle"
            size="md"
            icon="lucide-plus"
            label="New discussion"
            @click="showNewDiscussionDialog = true"
          />
        </template>
        <Button
          v-else
          variant="subtle"
          theme="red"
          size="md"
          :disabled="selectedDrafts.length === 0"
          @click="showDeleteConfirm = true"
        >
          Delete{{ selectedDrafts.length ? ` ${selectedDrafts.length}` : '' }}
        </Button>
      </div>
    </template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs class="h-7" :items="[{ label: 'Drafts', route: { name: 'Drafts' } }]" />
    <div class="flex items-center gap-2">
      <template v-if="!isBulkDeleteMode">
        <Button
          v-show="drafts.data?.length"
          variant="ghost"
          icon-left="lucide-square-check"
          @click="isBulkDeleteMode = true"
        >
          Select
        </Button>
        <Button
          v-if="!readOnlyMode"
          variant="subtle"
          icon-left="lucide-plus"
          @click="showNewDiscussionDialog = true"
        >
          New discussion
        </Button>
      </template>
      <template v-else>
        <Button variant="ghost" @click="cancelBulkDelete">Cancel</Button>
        <Button
          v-if="selectedDrafts.length > 0"
          theme="red"
          icon-left="lucide-trash-2"
          @click="showDeleteConfirm = true"
        >
          Delete {{ selectedDrafts.length }} draft{{ selectedDrafts.length > 1 ? 's' : '' }}
        </Button>
      </template>
    </div>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <div>
      <EmptyStateBox v-if="drafts.data?.length === 0" class="mx-3">
        <span class="lucide-coffee h-7 w-7 text-ink-gray-4" />
        No drafts
      </EmptyStateBox>
      <div class="-mx-3" v-else>
        <List
          :selectable="isBulkDeleteMode"
          v-model:selection="selectedDrafts"
          divider="inset"
          class="list-gap-4"
        >
          <ListRow
            v-for="draft in drafts.data"
            :key="draft.name"
            :to="draftRoute(draft)"
            :value="draft.name"
            class="h-15"
          >
            <ListCell>
              <UserAvatarWithHover :user="draft.owner" size="2xl" />
            </ListCell>
            <ListCell>
              <div class="min-w-0 flex-1">
                <div class="flex items-center min-w-0 gap-1.5">
                  <Tooltip v-if="draft.kind === 'comment'" text="Reply draft">
                    <span class="lucide-reply h-4 w-4 shrink-0 text-ink-gray-5" />
                  </Tooltip>
                  <span
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-ink-gray-8 text-base-medium"
                  >
                    {{ draft.title }}
                  </span>
                </div>
                <div class="flex mt-1.5 items-center min-w-0">
                  <div
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-base inline-flex items-center text-ink-gray-5"
                  >
                    <div v-if="draft.space_title" class="inline-flex items-center">
                      <span>{{ draft.space_title }}</span>
                      <span
                        v-if="draft.is_private"
                        class="lucide-lock h-3 w-3 text-ink-gray-6 ml-0.5"
                      />
                      <span>:&nbsp;</span>
                    </div>
                    <span class="overflow-hidden text-ellipsis whitespace-nowrap">
                      {{ contentPreview(draft.content) }}
                    </span>
                  </div>
                </div>
              </div>
            </ListCell>
            <ListCell class="justify-end">
              <Tooltip :text="dayjsLocal(draft.modified).format('D MMM YYYY [at] h:mm A')">
                <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
                  {{ relativeTimestamp(draft.modified) }}
                </div>
              </Tooltip>
            </ListCell>
          </ListRow>
        </List>
      </div>
    </div>
  </div>

  <Dialog
    title="Delete drafts"
    message="Are you sure you want to delete selected drafts? This action cannot be undone."
    :actions="[
      {
        label: 'Delete',
        variant: 'solid',
        theme: 'red',
        onClick: deleteDrafts,
      },
    ]"
    v-model:open="showDeleteConfirm"
  />

  <NewDiscussionSpaceDialog v-model="showNewDiscussionDialog" />
</template>
<script setup lang="ts">
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Tooltip,
  dayjsLocal,
  Breadcrumbs,
  Button,
  Dialog,
  useCall,
  toast,
} from 'frappe-ui'
import { List, ListRow, ListCell } from 'frappe-ui/list'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import NewDiscussionSpaceDialog from '@/components/NewDiscussionSpaceDialog.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { relativeTimestamp } from '@/utils'
import { onMounted, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { recoverOrphanedDrafts } from '@/data/useDraftSync'
import { drafts, type DraftRow } from '@/data/drafts'

interface DeleteDraftsResponse {
  deleted: string[]
  failed: { name: string; error: string }[]
  total: number
  success_count: number
  failure_count: number
}

const isBulkDeleteMode = ref(false)
const selectedDrafts = ref<string[]>([])
const showDeleteConfirm = ref(false)
const showNewDiscussionDialog = ref(false)

// Comment drafts always open their parent discussion with the reply composer focused
// (?draft=comment) — never the new-discussion composer, which would resurface a saved reply
// as a brand-new discussion. Discussion drafts open the scoped composer; those without a
// resolvable community fall back to the unscoped route.
function draftRoute(draft: DraftRow): RouteLocationRaw {
  if (draft.kind === 'comment' && draft.discussion && draft.space) {
    // When the community resolved server-side, route fully scoped. Otherwise use the
    // space-scoped path and let the router fill in the community — so the reply still opens
    // in place (and its content is never silently rerouted into a new discussion).
    if (draft.community) {
      return {
        name: 'Discussion',
        params: {
          communityId: draft.community,
          spaceId: draft.space,
          postId: draft.discussion,
        },
        query: { draft: 'comment' },
      }
    }
    return {
      path: `/space/${draft.space}/discussion/${draft.discussion}`,
      query: { draft: 'comment' },
    }
  }

  if (!draft.community) {
    return { name: 'LegacyNewDiscussion', query: { draft: draft.name } }
  }

  return {
    name: 'NewDiscussion',
    params: { communityId: draft.community },
    query: { draft: draft.name },
  }
}

function cancelBulkDelete() {
  isBulkDeleteMode.value = false
  selectedDrafts.value = []
}

let deleteDraftsCall = useCall<DeleteDraftsResponse, { names: string[] }>({
  url: '/api/v2/method/GP Draft/bulk_delete',
  method: 'POST',
  immediate: false,
})

function deleteDrafts() {
  deleteDraftsCall
    .submit({ names: selectedDrafts.value })
    .then(() => {
      let response = deleteDraftsCall.data
      let deletedCount = response?.success_count || 0
      let failedCount = response?.failure_count || 0

      // bulk_delete is a custom method, so the doctype APIs never saw these deletes —
      // drop the rows the list is still holding.
      response?.deleted.forEach((name) => drafts.removeRow(name))

      if (deletedCount > 0) {
        toast.success(deletedCount === 1 ? 'Draft deleted' : `${deletedCount} drafts deleted`)
      }

      if (failedCount > 0) {
        selectedDrafts.value = response?.failed.map((f) => f.name) || []
        toast.error(
          failedCount === 1
            ? '1 draft could not be deleted'
            : `${failedCount} drafts could not be deleted`,
        )
        showDeleteConfirm.value = false
        return
      }

      selectedDrafts.value = []
      showDeleteConfirm.value = false
      isBulkDeleteMode.value = false
    })
    .catch(() => {
      toast.error('Failed to delete drafts')
      showDeleteConfirm.value = false
    })
}

// Drafts whose server row never got created (a push that never landed) live only in
// IndexedDB and would otherwise never show here. Adopting one inserts it through the list,
// which is what puts it on screen.
onMounted(() => {
  recoverOrphanedDrafts()
})

function contentPreview(content?: string | null) {
  if (content) {
    // remove html tags
    return content.replace(/<[^>]*>?/gm, '').slice(0, 100)
  }
}
</script>
