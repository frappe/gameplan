<template>
  <div>
    <PageHeaderMobile class="sm:hidden" title="Pages">
      <template #prefix>
        <PageHeaderBackButton :to="{ name: 'More' }" />
      </template>
      <template #suffix>
        <Select :options="sortOptions" v-model="orderBy" />
      </template>
    </PageHeaderMobile>
    <PageHeader class="hidden sm:flex">
      <Breadcrumbs class="h-7" :items="[{ label: 'My Pages', route: { name: 'MyPages' } }]" />
      <div class="flex items-center space-x-2">
        <Select :options="sortOptions" v-model="orderBy" />
      </div>
    </PageHeader>

    <div class="px-3 sm:px-5 mt-5">
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
import { PageHeaderBackButton, PageHeaderMobile, PageHeader, Select, Breadcrumbs } from 'frappe-ui'
import { useNewDoc } from 'frappe-ui'
import { useSessionUser } from '@/data/users'
import PageGrid from './PageGrid.vue'
import { GPPage } from '@/types/doctypes'
import { UseListOptions } from 'frappe-ui'

const router = useRouter()
const sessionUser = useSessionUser()
const orderBy: UseListOptions<GPPage>['orderBy'] = ref('modified desc')

const sortOptions = [
  { label: 'Sort by', value: '', disabled: true },
  { label: 'Page Title', value: 'title asc' },
  { label: 'Date Updated', value: 'modified desc' },
  { label: 'Date Created', value: 'creation desc' },
]

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
