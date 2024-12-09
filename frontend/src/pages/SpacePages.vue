<template>
  <div class="mx-auto max-w-4xl px-5">
    <div class="mt-5 flex items-center justify-between">
      <div class="text-xl font-semibold">Pages</div>
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
          Add new
        </Button>
      </div>
    </div>
    <PageGrid class="mt-4.5" :listOptions="{ filters: { project: space.name }, orderBy }" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Dropdown } from 'frappe-ui'
import ArrowDownUp from '~icons/lucide/arrow-up-down'
import PageGrid from './PageGrid.vue'
import { useNewDoc } from '@/data/newDoc'

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
