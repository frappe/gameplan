<template>
  <div v-if="pages.data?.length">
    <div v-for="(page, index) in pages.data" :key="page.name">
      <router-link
        :to="{
          name: 'ProjectPage',
          params: {
            teamId: page.team,
            projectId: page.project,
            pageId: page.name,
          },
        }"
        class="flex h-15 items-start rounded-md p-2.5 hover:bg-surface-gray-2"
      >
        <div>
          <div class="text-base font-medium leading-4 text-ink-gray-8">
            {{ page.title }}
          </div>
          <div class="mt-1.5 flex items-center">
            <div class="flex items-center space-x-1.5">
              <UserAvatar :user="page.owner" size="xs" />
              <span class="text-base text-ink-gray-5">{{ $user(page.owner).full_name }}</span>
            </div>
            <span class="px-2 text-ink-gray-5">&middot;</span>
            <span class="text-base text-ink-gray-5">
              Updated {{ dayjsLocal(page.modified).fromNow() }}
            </span>
          </div>
        </div>
      </router-link>
      <div class="mx-2.5 border-b" v-if="index < pages.data.length - 1"></div>
    </div>
  </div>
  <div
    class="flex flex-col items-center rounded-lg border-2 border-dashed py-8 text-base text-ink-gray-5"
    v-else
  >
    No pages
  </div>
</template>
<script setup>
import { createListResource, dayjsLocal } from 'frappe-ui'

let props = defineProps({
  listOptions: {
    type: Object,
    default: () => ({}),
  },
})

let pages = createListResource({
  type: 'list',
  doctype: 'GP Page',
  cache: ['Pages', props.listOptions],
  fields: ['name', 'title', 'slug', 'modified', 'owner', 'project', 'team'],
  filters: props.listOptions.filters,
  pageLength: props.listOptions.pageLength || 20,
  auto: true,
  realtime: true,
  orderBy: props.listOptions.orderBy || 'modified desc',
})
</script>
