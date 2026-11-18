<template>
  <div class="mt-5 body-container">
    <SpaceHeaderActions>
      <Button
        v-if="canEditSpace"
        variant="solid"
        icon-left="lucide-plus"
        label="New page"
        :loading="newPage.loading"
        @click="createNewPage"
      />
    </SpaceHeaderActions>
    <div class="mb-4 flex items-center justify-between gap-2">
      <SpaceTabs :spaceId="spaceId" />
      <div class="flex shrink-0 items-center gap-2">
        <Select class="!w-fit" :options="sortOptions" v-model="orderBy" />
        <!-- SpaceHeaderActions sits in the desktop header, so phones get their own button. -->
        <Button
          v-if="canEditSpace"
          class="sm:hidden"
          variant="solid"
          icon-left="lucide-plus"
          label="New"
          :loading="newPage.loading"
          @click="createNewPage"
        />
      </div>
    </div>
    <PageGrid
      :key="spaceId"
      class="grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-3 lg:grid-cols-4"
      :listOptions="{ filters: { project: spaceId }, orderBy: () => orderBy, limit: 99999 }"
      :readOnly="!canEditSpace"
    />
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Select, toast, useNewDoc, type UseListOptions } from 'frappe-ui'
import SpaceTabs from '@/components/SpaceTabs.vue'
import SpaceHeaderActions from '@/components/SpaceHeaderActions.vue'
import PageGrid from './PageGrid.vue'
import type { GPPage } from '@/types/doctypes'
import { useSpace } from '@/data/spaces'
import { readOnlyMode } from '@/data/readOnlyMode'
import { useSessionUser } from '@/data/users'
import { errorText } from '@/utils'
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

const sortOptions = [
  { label: 'Last updated', value: 'modified desc' },
  { label: 'Created', value: 'creation desc' },
  { label: 'Alphabetical', value: 'title asc' },
]

const newPage = useNewDoc<GPPage>('GP Page', {
  project: props.spaceId,
  title: 'Untitled',
  content: '',
})

function createNewPage() {
  newPage.doc.project = props.spaceId
  newPage
    .submit()
    .then((doc) => {
      router.push({
        name: 'SpacePage',
        params: {
          communityId: space.value?.team,
          spaceId: props.spaceId,
          pageId: doc.name,
          slug: doc.slug,
        },
      })
    })
    .catch((error: unknown) => toast.error(errorText(error, 'Could not create the page.')))
}
</script>
