<template>
  <div class="body-container mt-5">
    <SpaceHeaderActions>
      <template v-if="!isBulkMoveMode">
        <DropdownMoreOptions
          align="end"
          :options="[
            {
              label: 'Move discussions',
              icon: 'lucide-log-out',
              onClick: () => (isBulkMoveMode = true),
            },
          ]"
        />
        <Button
          variant="solid"
          icon-left="lucide-plus"
          @click="router.push({ name: 'NewDiscussion', query: { spaceId: spaceId } })"
        >
          Add new
        </Button>
      </template>
      <template v-else>
        <Button variant="ghost" @click="cancelBulkMove">Cancel</Button>
        <Button
          variant="solid"
          icon-left="lucide-log-out"
          @click="showMoveDialog = true"
          :disabled="selectedDiscussions.length === 0"
        >
          <template v-if="selectedDiscussions.length === 0">Move discussions</template>
          <template v-else>
            Move {{ selectedDiscussions.length }} discussion{{
              selectedDiscussions.length > 1 ? 's' : ''
            }}
          </template>
        </Button>
      </template>
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center">
      <SpaceTabs :spaceId="spaceId" />
    </div>
    <DiscussionList
      class="-mx-3"
      ref="discussionListRef"
      :filters="() => ({ project: spaceId })"
      :cacheKey="`SpaceDiscussions-${spaceId}`"
      :selectable="isBulkMoveMode"
      :selectedDiscussions="selectedDiscussions"
      @toggle-selection="toggleSelection"
    />
    <Dialog
      title="Move discussions to another space"
      @close="resetMoveDialog"
      v-model:open="showMoveDialog"
    >
      <Combobox
        :options="spaceOptions"
        v-model="selectedSpace"
        placeholder="Select a space"
        class="w-full"
        open-on-click
        autofocus
      />
      <ErrorMessage class="mt-2" :message="bulkMoveDiscussions.error" />
      <template #actions>
        <Button
          class="w-full"
          variant="solid"
          :loading="bulkMoveDiscussions.loading"
          :disabled="!selectedSpace"
          @click="moveDiscussions"
        >
          {{ selectedSpace ? `Move to ${selectedSpaceTitle}` : 'Move' }}
        </Button>
      </template>
    </Dialog>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { Combobox, Dialog, ErrorMessage, useCall, toast } from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import SpaceTabs from '@/components/SpaceTabs.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useSpace, spaces } from '@/data/spaces'

interface BulkUpdateResponse {
  moved: string[]
  failed: { name: string; error: string }[]
  total: number
  success_count: number
  failure_count: number
}

const props = defineProps<{
  spaceId: string
}>()

const isBulkMoveMode = ref(false)
const selectedDiscussions = ref<string[]>([])
const showMoveDialog = ref(false)
const selectedSpace = ref<string | null>(null)
const discussionListRef = useTemplateRef('discussionListRef')
const router = useRouter()
const selectedSpaceTitle = computed(() => {
  return selectedSpace.value ? useSpace(selectedSpace.value).value?.title : ''
})

const spaceOptions = useGroupedSpaceOptions({
  filterFn: (space) => !space.archived_at && space.name !== props.spaceId,
})

const bulkMoveDiscussions = useCall<
  BulkUpdateResponse,
  { discussions: { name: string; project: string }[] }
>({
  url: '/api/v2/method/GP Discussion/move_discussions',
  method: 'POST',
  immediate: false,
})

function toggleSelection(name: string) {
  if (selectedDiscussions.value.includes(name)) {
    selectedDiscussions.value = selectedDiscussions.value.filter((value) => value !== name)
  } else {
    selectedDiscussions.value.push(name)
  }
}

function cancelBulkMove() {
  isBulkMoveMode.value = false
  selectedDiscussions.value = []
}

function resetMoveDialog() {
  selectedSpace.value = null
}

function moveDiscussions() {
  if (selectedDiscussions.value.length === 0) {
    toast.error('Select discussions to move')
    return
  }
  if (!selectedSpace.value) {
    toast.error('Select a space to move discussions')
    return
  }

  bulkMoveDiscussions
    .submit({
      discussions: selectedDiscussions.value.map((name) => ({
        name,
        project: selectedSpace.value as string,
      })),
    })
    .then(() => {
      const response = bulkMoveDiscussions.data
      const successCount = response?.success_count || 0
      const failureCount = response?.failure_count || 0

      if (successCount > 0) {
        toast.success(successCount === 1 ? 'Discussion moved' : `${successCount} discussions moved`)
      }

      if (failureCount > 0) {
        selectedDiscussions.value = response?.failed.map((item) => item.name) || []
        toast.error(
          failureCount === 1
            ? '1 discussion could not be moved'
            : `${failureCount} discussions could not be moved`,
        )
        resetMoveDialog()
        showMoveDialog.value = false
        return
      }

      spaces.reload()
      if (discussionListRef.value) {
        discussionListRef.value.discussions?.reload()
        discussionListRef.value.pinnedDiscussions?.reload()
      }
      resetMoveDialog()
      selectedDiscussions.value = []
      showMoveDialog.value = false
      isBulkMoveMode.value = false
    })
    .catch(() => {
      toast.error(bulkMoveDiscussions.error || 'Failed to move discussions')
    })
}
</script>
