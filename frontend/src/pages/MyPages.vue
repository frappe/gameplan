<template>
  <header class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5">
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

      <Button variant="solid" @click="$resources.newPage.submit()">
        <template #prefix>
          <LucidePlus class="h-4 w-4" />
        </template>
        Add new
      </Button>
    </div>
  </header>
  <div class="mx-auto w-full max-w-4xl px-5">
    <div class="py-6">
      <PageGrid
        :listOptions="{
          filters: { owner: $user().name },
          orderBy,
        }"
      />
    </div>
  </div>
</template>
<script>
import { Dropdown, Select, Breadcrumbs } from 'frappe-ui'
import ArrowDownUp from '~icons/lucide/arrow-up-down'
import PageGrid from './PageGrid.vue'

export default {
  name: 'MyPages',
  components: { Dropdown, Select, ArrowDownUp, PageGrid, Breadcrumbs },
  data() {
    return {
      orderBy: 'modified desc',
    }
  },
  resources: {
    newPage() {
      return {
        url: 'frappe.client.insert',
        params: {
          doc: {
            doctype: 'GP Page',
            title: 'Untitled',
            content: '',
          },
        },
        onSuccess(doc) {
          this.$router.push({
            name: 'Page',
            params: { pageId: doc.name },
          })
        },
      }
    },
  },
  pageMeta() {
    return {
      title: 'My Pages',
    }
  },
}
</script>
<style scoped>
.sort-button:deep(.feather-minimize-2) {
  transform: rotate(15deg);
}
</style>
