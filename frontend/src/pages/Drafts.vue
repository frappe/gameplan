<template>
  <PageHeaderMobile class="sm:hidden" title="Drafts">
    <template #prefix>
      <Button v-if="isBulkDeleteMode" variant="ghost" size="md" @click="cancelBulkDelete">
        Cancel
      </Button>
      <PageHeaderBackButton v-else :fallback-route="{ name: 'More' }" />
    </template>
    <template #suffix>
      <div class="flex items-center gap-2">
        <template v-if="!isBulkDeleteMode">
          <DropdownMoreOptions
            v-if="draftRows.length"
            label="Draft actions"
            button-size="md"
            align="end"
            :options="draftActions"
          />
          <Button
            v-if="!readOnlyMode"
            variant="solid"
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
          @click="confirmDeleteDrafts"
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
        <DropdownMoreOptions
          v-if="draftRows.length"
          label="Draft actions"
          align="end"
          :options="draftActions"
        />
        <Button
          v-if="!readOnlyMode"
          variant="solid"
          icon-left="lucide-plus"
          label="New discussion"
          @click="showNewDiscussionDialog = true"
        />
      </template>
      <template v-else>
        <Button variant="ghost" @click="cancelBulkDelete">Cancel</Button>
        <Button
          v-if="selectedDrafts.length > 0"
          theme="red"
          icon-left="lucide-trash-2"
          @click="confirmDeleteDrafts"
        >
          Delete {{ draftCountLabel(selectedDrafts.length) }}
        </Button>
      </template>
    </div>
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <div>
      <div v-if="phase === 'skeleton'" class="-mx-3">
        <ListRowSkeleton
          v-for="index in 3"
          :key="index"
          :show-separator="index < 3"
          label="Loading draft"
        />
      </div>
      <LoadError
        v-else-if="phase === 'failed'"
        :message="errorText(drafts.error, 'Could not load your drafts.')"
        @retry="drafts.reload()"
      />
      <EmptyStateBox
        v-else-if="phase === 'empty'"
        icon="lucide-file-pen-line"
        title="No drafts"
        description="Discussions you start and don't publish are saved here."
      />
      <div class="-mx-3" v-else>
        <List
          :selectable="isBulkDeleteMode"
          v-model:selection="selectedDrafts"
          divider="inset"
          class="list-gap-4"
        >
          <ListRow
            v-for="draft in draftRows"
            :key="draft.name"
            :route="draftRoute(draft)"
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
                    {{ draft.title || 'Untitled draft' }}
                  </span>
                  <Tooltip
                    v-if="draft.scheduled_at"
                    :text="`Scheduled for ${dayjsLocal(draft.scheduled_at).format(
                      'ddd D MMM, h:mm A',
                    )}`"
                  >
                    <span class="lucide-calendar-clock size-4 shrink-0 text-ink-gray-5" />
                  </Tooltip>
                </div>
                <div class="flex mt-1.5 items-center min-w-0">
                  <div
                    class="flex min-w-0 items-center overflow-hidden whitespace-nowrap text-base text-ink-gray-5"
                  >
                    <div v-if="draft.space_title" class="inline-flex shrink-0 items-center">
                      <span>{{ placeLabel(draft) }}</span>
                      <span
                        v-if="draft.is_private"
                        class="lucide-lock h-3 w-3 text-ink-gray-6 ml-0.5"
                      />
                      <span>:&nbsp;</span>
                    </div>
                    <span class="min-w-0 truncate">
                      {{ contentPreview(draft.content) }}
                    </span>
                  </div>
                </div>
              </div>
            </ListCell>
            <ListCell class="justify-end">
              <Tooltip :text="fullTimestamp(draft.modified)">
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
  useCall,
  toast,
} from 'frappe-ui'
import { List, ListRow, ListCell } from 'frappe-ui/list'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import ListRowSkeleton from '@/components/ListRowSkeleton.vue'
import LoadError from '@/components/LoadError.vue'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import NewDiscussionSpaceDialog from '@/components/NewDiscussionSpaceDialog.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { errorText, fullTimestamp, relativeTimestamp } from '@/utils'
import { confirmDelete } from '@/utils/confirmDelete'
import { getCommunity } from '@/data/communities'
import { computed, onMounted, onScopeDispose, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { deleteDraft, recoverOrphanedDrafts } from '@/data/useDraftSync'
import { drafts, listLocalDrafts, type DraftRow } from '@/data/drafts'
import { broadcastDraftChange, deleteDraftRecord, onDraftChange } from '@/data/draftStore'
import { whenOnline, refuseOffline } from '@/data/online'
import { captureError } from '@/utils/errorReporting'

interface DeleteDraftsResponse {
  deleted: string[]
  failed: { name: string; error: string }[]
  total: number
  success_count: number
  failure_count: number
}

const isBulkDeleteMode = ref(false)
const selectedDrafts = ref<string[]>([])
const showNewDiscussionDialog = ref(false)

// Drafts started offline are only on this device until they are saved to the server. They
// keep the same name there, so a row is listed once either way.
const localDrafts = ref<DraftRow[]>([])
const draftRows = computed(() => {
  const saved = drafts.data ?? []
  const onServer = new Set(saved.map((draft) => draft.name))
  return [...localDrafts.value.filter((draft) => !onServer.has(draft.name)), ...saved]
})
const isLocalOnly = (name: string) =>
  localDrafts.value.some((draft) => draft.name === name) &&
  !drafts.data?.some((draft) => draft.name === name)

function loadLocalDrafts() {
  listLocalDrafts()
    .then((rows) => (localDrafts.value = rows))
    .catch((error) => captureError(error, { action: 'list-local-drafts' }))
}
onScopeDispose(onDraftChange(loadLocalDrafts))

// useList keeps `data` undefined until the first load lands, and after it fails. Drafts only
// on this device are rows too.
const phase = computed(() => {
  if (draftRows.value.length) return 'rows'
  if (drafts.data) return 'empty'
  if (drafts.error && !drafts.loading) return 'failed'
  return 'skeleton'
})

const draftActions = [
  {
    label: 'Select drafts',
    icon: 'lucide-square-check',
    onClick: () => (isBulkDeleteMode.value = true),
  },
]

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

function confirmDeleteDrafts() {
  const count = selectedDrafts.value.length
  confirmDelete({
    title: `Delete ${draftCountLabel(count)}?`,
    message:
      count === 1
        ? "The draft will be deleted. This can't be undone."
        : "The drafts will be deleted. This can't be undone.",
    onDelete: deleteDrafts,
  })
}

async function deleteDrafts() {
  const local = selectedDrafts.value.filter(isLocalOnly)
  const saved = selectedDrafts.value.filter((name) => !isLocalOnly(name))
  // A draft on the server can only be deleted with the connection. The selection stays.
  if (saved.length && refuseOffline()) return
  // One a save reached meanwhile is deleted on the server as well, as its only writer.
  const results = await Promise.allSettled(local.map((name) => deleteDraft(name)))
  const localFailed = local.filter((_, i) => results[i].status === 'rejected')
  loadLocalDrafts()
  if (!saved.length) return reportDelete(local.length - localFailed.length, localFailed)

  return deleteDraftsCall
    .submit({ names: saved })
    .then(() => {
      const response = deleteDraftsCall.data
      // bulk_delete is a custom method, so the doctype APIs never saw these deletes —
      // drop the rows the list is still holding, and their copies on this device.
      response?.deleted.forEach((name) => {
        drafts.removeRow(name)
        void deleteDraftRecord(name).then(() => broadcastDraftChange(name))
      })
      const failed = [...localFailed, ...(response?.failed.map((f) => f.name) ?? [])]
      reportDelete((response?.success_count || 0) + local.length - localFailed.length, failed)
    })
    .catch(() => reportDelete(local.length - localFailed.length, [...localFailed, ...saved]))
}

/** `failed` stay selected, to try again. */
function reportDelete(deletedCount: number, failed: string[]) {
  if (deletedCount > 0) {
    toast.success(deletedCount === 1 ? 'Draft deleted' : `${deletedCount} drafts deleted`)
  }
  if (failed.length) {
    selectedDrafts.value = failed
    toast.error(
      failed.length === 1
        ? '1 draft could not be deleted'
        : `${failed.length} drafts could not be deleted`,
    )
    return
  }
  selectedDrafts.value = []
  isBulkDeleteMode.value = false
}

// Drafts with edits the server has not seen (started offline, or a push that never landed)
// are saved under their own names, which puts them on the server's list.
onMounted(() => {
  loadLocalDrafts()
  // Rows the composer inserted or edited this session hold the bare GP Draft fields, with no
  // space title, community or kind. Refetch so every row has its place and route.
  if (drafts.isFinished) drafts.reload()
  // Offline that can only fail, so it waits for the connection.
  whenOnline(() => recoverOrphanedDrafts().finally(loadLocalDrafts))
})

function draftCountLabel(count: number) {
  return count === 1 ? '1 draft' : `${count} drafts`
}

function placeLabel(draft: DraftRow) {
  const communityTitle = draft.community ? getCommunity(draft.community)?.title : undefined
  return [communityTitle, draft.space_title].filter(Boolean).join(' / ')
}

// One line of plain text. Block tags become spaces so paragraphs do not run together;
// the row's text-ellipsis does the cutting.
function contentPreview(content?: string | null) {
  if (!content) return ''
  const spaced = content.replace(/<\/?(p|div|li|h[1-6]|blockquote|pre|br)\b[^>]*>/gi, ' ')
  const text = new DOMParser().parseFromString(spaced, 'text/html').body.textContent ?? ''
  return text.replace(/\s+/g, ' ').trim()
}
</script>
