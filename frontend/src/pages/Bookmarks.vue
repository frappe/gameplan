<template>
  <PageHeaderMobile class="sm:hidden" title="Bookmarks">
    <template #prefix>
      <PageHeaderBackButton :to="{ name: 'More' }" />
    </template>
  </PageHeaderMobile>
  <PageHeader class="hidden sm:flex">
    <Breadcrumbs class="h-7" :items="[{ label: 'Bookmarks', route: { name: 'Bookmarks' } }]" />
  </PageHeader>
  <div class="body-container pt-5 pb-40">
    <DiscussionList
      class="-mx-3"
      :filters="{ feed_type: 'bookmarks' }"
      :show-pinned="false"
      cacheKey="Bookmarks"
    />
  </div>
</template>

<script setup lang="ts">
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  usePageMeta,
} from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'

usePageMeta(() => ({ title: 'Bookmarks' }))
</script>
