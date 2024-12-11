<template>
  <div class="mt-5 mx-auto max-w-4xl px-2 sm:px-5" v-if="space.doc">
    <div class="flex px-3 mb-4 items-center justify-between">
      <SpaceTabs :spaceId="space.doc.name" />
      <div class="flex items-center space-x-2">
        <Dropdown
          :options="[
            {
              label: 'Page Title',
              onClick: () => (orderBy = 'title asc'),
            },
            {
              label: 'Date Updated',
              onClick: () => (orderBy = 'modified desc'),
            },
            {
              label: 'Date Created',
              onClick: () => (orderBy = 'creation desc'),
            },
          ]"
          placement="center"
        >
          <Button>
            <div class="flex items-center">
              <ArrowDownUp class="mr-1.5 h-4 w-4 leading-none" :stroke-width="1.5" />
              <span> Sort </span>
            </div>
          </Button>
        </Dropdown>
        <Button variant="solid" @click="createNewPage">
          <template #prefix><LucidePlus class="w-4" /></template>
          <span class="whitespace-nowrap"> Add new </span>
        </Button>
      </div>
    </div>
    <PageGrid class="px-3" :listOptions="{ filters: { project: space.name }, orderBy }" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Dropdown } from 'frappe-ui'
import { useNewDoc } from '@/data/newDoc'
import SpaceTabs from '@/components/SpaceTabs.vue'
import PageGrid from './PageGrid.vue'

import ArrowDownUp from '~icons/lucide/arrow-up-down'

const props = defineProps<{
  space: Object
}>()

const router = useRouter()
const orderBy = ref('modified desc')

const newPage = useNewDoc('GP Page', {
  project: props.space.doc.name,
  title: 'Untitled',
  content: '',
})

function createNewPage() {
  newPage.submit().then((doc) => {
    router.push({
      name: 'ProjectPage',
      params: { pageId: doc.name },
    })
  })
}
</script>
<style scoped>
.sort-button:deep(.feather-minimize-2) {
  transform: rotate(15deg);
}
</style>
