<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
  >
    <Breadcrumbs class="h-7" :items="[{ label: 'My Pages', route: { name: 'MyPages' } }]" />
    <div class="flex items-center space-x-2">
      <Select
        :options="[
          {
            label: 'Sort by',
            value: '',
            disabled: true,
          },
          {
            label: 'Page Title',
            value: 'title asc',
          },
          {
            label: 'Date Updated',
            value: 'modified desc',
          },
          {
            label: 'Date Created',
            value: 'creation desc',
          },
        ]"
        v-model="orderBy"
      />

      <Button variant="solid" @click="createNewPage">
        <template #prefix>
          <LucidePlus class="h-4 w-4" />
        </template>
        Add new
      </Button>
    </div>
  </header>
  <div class="mx-auto w-full max-w- px-5">
    <div class="py-6">
      <PageGrid
        class="grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6"
        :listOptions="{
          filters: { owner: sessionUser.name },
          orderBy: () => orderBy,
        }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Select, Breadcrumbs } from 'frappe-ui'
import { useNewDoc } from 'frappe-ui/src/data-fetching'
import { useSessionUser } from '@/data/users'
import PageGrid from './PageGrid.vue'
import { GPPage } from '@/types/doctypes'
import { UseListOptions } from 'frappe-ui/src/data-fetching/useList/types'

const router = useRouter()
const sessionUser = useSessionUser()
const orderBy: UseListOptions<GPPage>['orderBy'] = ref('modified desc')

const newPage = useNewDoc<GPPage>('GP Page', {
  title: 'Untitled',
  content: '',
})

function createNewPage() {
  newPage.submit().then((doc) => {
    router.push({
      name: 'Page',
      params: { pageId: doc.name, slug: doc.slug },
    })
  })
}
</script>
