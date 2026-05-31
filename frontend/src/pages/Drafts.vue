<template>
  <PageHeader>
    <Breadcrumbs class="h-7" :items="[{ label: 'Drafts', route: { name: 'Drafts' } }]" />
    <div class="flex items-center gap-2">
      <template v-if="!isBulkDeleteMode">
        <DropdownMoreOptions
          align="end"
          :options="[
            {
              label: 'Delete drafts',
              icon: 'lucide-trash-2',
              onClick: () => (isBulkDeleteMode = true),
            },
          ]"
        />
        <Button
          icon-left="lucide-plus"
          variant="solid"
          @click="router.push({ name: 'NewDiscussion' })"
        >
          Add new
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
        <template v-for="(draft, index) in drafts.data" :key="draft.name">
          <RouterLink
            :to="{ name: 'NewDiscussion', query: { draft: draft.name } }"
            custom
            v-slot="{ href, navigate }"
          >
            <a
              :href="href"
              class="flex items-center py-2 px-3 group relative h-15 rounded-[10px] transition hover:bg-surface-gray-2 cursor-pointer"
              @click="handleDraftRowClick($event, navigate, draft.name)"
            >
              <motion.div
                class="flex shrink-0 items-center overflow-hidden"
                :animate="{ width: isBulkDeleteMode ? 32 : 0 }"
                :transition="{ type: 'spring', stiffness: 700, damping: 48, mass: 0.5 }"
              >
                <AnimatePresence>
                  <motion.div
                    v-if="isBulkDeleteMode"
                    class="flex items-center"
                    role="checkbox"
                    :aria-checked="selectedDrafts.includes(draft.name)"
                    tabindex="0"
                    :initial="{ scale: 0 }"
                    :animate="{ scale: 1 }"
                    :exit="{ scale: 0 }"
                    :transition="{ duration: 0.08, ease: 'easeOut' }"
                    @click.stop="toggleSelection(draft.name)"
                    @keydown.enter.prevent="toggleSelection(draft.name)"
                    @keydown.space.prevent="toggleSelection(draft.name)"
                  >
                    <Checkbox :modelValue="selectedDrafts.includes(draft.name)" />
                  </motion.div>
                </AnimatePresence>
              </motion.div>
              <UserAvatarWithHover :user="draft.owner" size="2xl" />
              <div class="ml-4 flex-1 min-w-0">
                <div class="flex items-center min-w-0">
                  <span
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-ink-gray-8 text-base font-medium"
                  >
                    {{ draft.title }}
                  </span>
                </div>
                <div class="flex mt-1.5 items-center min-w-0">
                  <div
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-base inline-flex items-center text-ink-gray-5"
                  >
                    <div v-if="draft.project_title" class="inline-flex items-center">
                      <span>{{ draft.project_title }}</span>
                      <span
                        v-if="isSpacePrivate(draft.project)"
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
              <div class="ml-auto shrink-0">
                <Tooltip :text="dayjsLocal(draft.modified).format('D MMM YYYY [at] h:mm A')">
                  <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
                    {{ relativeTimestamp(draft.modified) }}
                  </div>
                </Tooltip>
              </div>
            </a>
          </RouterLink>
          <div
            class="mx-3 h-px border-t border-outline-gray-modals transition-opacity group-hover:opacity-0"
            v-if="index < (drafts.data?.length || 0) - 1"
          ></div>
        </template>
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
</template>
<script setup lang="ts">
import {
  Tooltip,
  dayjsLocal,
  Breadcrumbs,
  Button,
  Checkbox,
  Dialog,
  useCall,
  toast,
} from 'frappe-ui'
import { GPDraft } from '@/types/doctypes'
import { useList } from 'frappe-ui'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import { useSpace } from '@/data/spaces'
import { relativeTimestamp } from '@/utils'
import PageHeader from '@/components/PageHeader.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { motion, AnimatePresence } from 'motion-v'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'

interface Draft extends GPDraft {
  project_title: string
}

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
const router = useRouter()

function toggleSelection(name: string) {
  if (selectedDrafts.value.includes(name)) {
    selectedDrafts.value = selectedDrafts.value.filter((n) => n !== name)
  } else {
    selectedDrafts.value.push(name)
  }
}

function cancelBulkDelete() {
  isBulkDeleteMode.value = false
  selectedDrafts.value = []
}

function handleDraftRowClick(
  event: MouseEvent,
  navigate: (event?: MouseEvent) => void,
  draftName: string,
) {
  if (isBulkDeleteMode.value) {
    event.preventDefault()
    toggleSelection(draftName)
    return
  }
  navigate(event)
}

let deleteDraftsCall = useCall<DeleteDraftsResponse, { names: string[] }>({
  url: '/api/v2/document/GP Draft/bulk_delete',
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
        drafts.reload()
        showDeleteConfirm.value = false
        return
      }

      drafts.reload()
      selectedDrafts.value = []
      showDeleteConfirm.value = false
      isBulkDeleteMode.value = false
    })
    .catch(() => {
      toast.error('Failed to delete drafts')
      showDeleteConfirm.value = false
    })
}

let drafts = useList<Draft>({
  doctype: 'GP Draft',
  filters: {
    type: 'Discussion',
  },
  fields: [
    'name',
    'title',
    'content',
    'project',
    'project.title as project_title',
    'creation',
    'modified',
    'owner',
  ],
  orderBy: 'creation desc',
  cacheKey: 'drafts',
})

function contentPreview(content?: string) {
  if (content) {
    // remove html tags
    return content.replace(/<[^>]*>?/gm, '').slice(0, 100)
  }
}

function isSpacePrivate(spaceId?: string) {
  if (!spaceId) return false
  return useSpace(spaceId).value?.is_private
}
</script>
