<template>
  <div class="mt-5 body-container">
    <SpaceHeaderActions>
      <Button v-if="canEditSpace" variant="solid" icon-left="lucide-plus" @click="createNewPage">
        <span class="whitespace-nowrap"> Add new </span>
      </Button>
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center justify-between">
      <SpaceTabs :spaceId="spaceId" />
      <Dropdown
        :options="[
          {
            label: 'Alphabetical',
            onClick: () => (orderBy = 'title asc'),
          },
          {
            label: 'Last updated',
            onClick: () => (orderBy = 'modified desc'),
          },
          {
            label: 'Created',
            onClick: () => (orderBy = 'creation desc'),
          },
        ]"
        align="end"
      >
        <template #default>
          <Button>
            <template #prefix>
              <span class="lucide-arrow-down-up me-1.5 h-4 w-4 leading-none" />
            </template>
            {{
              orderBy === 'title asc'
                ? 'Alphabetical'
                : orderBy === 'modified desc'
                  ? 'Last updated'
                  : 'Created'
            }}
          </Button>
        </template>
      </Dropdown>
    </div>
    <PageGrid
      class="grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-3 lg:grid-cols-4"
      :listOptions="{ filters: { project: spaceId }, orderBy: () => orderBy }"
      :readOnly="!canEditSpace"
    />
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Dropdown, useNewDoc, UseListOptions } from 'frappe-ui'
import SpaceTabs from '@/components/SpaceTabs.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import PageGrid from './PageGrid.vue'
import { GPPage } from '@/types/doctypes'
import { useSpace } from '@/data/spaces'
import { readOnlyMode } from '@/data/readOnlyMode'
import { useSessionUser } from '@/data/users'
import { isGuest } from '@/utils/permissions'

const props = defineProps<{
  spaceId: string
}>()

const router = useRouter()
const space = useSpace(() => props.spaceId)
const orderBy: UseListOptions<GPPage>['orderBy'] = ref('modified desc')
const canEditSpace = computed(
  () => !readOnlyMode && !space.value?.archived_at && !isGuest(useSessionUser()),
)

const newPage = useNewDoc<GPPage>('GP Page', {
  project: props.spaceId,
  title: 'Untitled',
  content: '',
})

function createNewPage() {
  newPage.submit().then((doc) => {
    router.push({
      name: 'SpacePage',
      params: { communityId: space.value?.team, spaceId: props.spaceId, pageId: doc.name },
    })
  })
}
</script>
<style scoped>
.sort-button:deep(.feather-minimize-2) {
  transform: rotate(15deg);
}
</style>
