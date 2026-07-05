<template>
  <div v-if="pages.data?.length === 0">
    <div class="col-span-full">
      <EmptyStateBox class="body-container">
        <span class="lucide-coffee h-7 w-7 text-ink-gray-4" />
        No pages
      </EmptyStateBox>
    </div>
  </div>
  <div v-else>
    <div class="relative" v-for="d in pages.data" :key="d.name">
      <router-link
        :to="
          d.project
            ? {
                name: 'SpacePage',
                params: {
                  communityId: d.team || getSpace(d)?.team,
                  pageId: d.name,
                  slug: d.slug,
                  spaceId: d.project,
                },
              }
            : { name: 'Page', params: { pageId: d.name, slug: d.slug } }
        "
      >
        <section class="group">
          <div
            class="aspect-[37/50] cursor-pointer overflow-hidden rounded-md dark:bg-gray-900 border border-gray-50 dark:border-outline-gray-1 p-3 shadow-lg transition-shadow hover:shadow-xl"
          >
            <div class="overflow-hidden text-ellipsis whitespace-nowrap">
              <div
                class="prose prose-v3 pointer-events-none w-[200%] origin-top-left scale-[.55] md:w-[250%] md:scale-[.39]"
                v-html="d.content"
              />
            </div>
          </div>
          <div class="mt-3 flex justify-between items-center">
            <div class="flex-grow w-full min-w-0">
              <h1 class="text-base-semibold truncate text-ink-gray-7">
                {{ d.title }}
              </h1>
              <div
                class="mt-1.5 text-sm flex gap-1 text-ink-gray-6"
                v-if="d.project"
                :set="(space = getSpace(d))"
              >
                <SpaceIcon :icon="space?.icon" class="size-4 text-ink-gray-6" />
                <div>{{ space?.title }}</div>
              </div>
            </div>
            <div v-if="!readOnly" class="shrink-0 ml-1 invisible group-hover:visible">
              <Dropdown
                :button="{
                  icon: 'lucide-more-horizontal',
                  label: 'Page Options',
                  variant: 'ghost',
                }"
                :options="getDropdownOptions(d)"
                align="end"
              />
            </div>
          </div>
        </section>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Dropdown, useList, UseListOptions, dialog } from 'frappe-ui'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { GPPage } from '@/types/doctypes'
import { useSpace } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import { canDeleteContent } from '@/utils/permissions'

const props = defineProps<{
  listOptions: {
    filters: UseListOptions<GPPage>['filters']
    orderBy?: UseListOptions<GPPage>['orderBy']
  }
  readOnly?: boolean
}>()

interface Page
  extends Pick<
    GPPage,
    'name' | 'creation' | 'title' | 'content' | 'slug' | 'project' | 'team' | 'modified' | 'owner'
  > {}

const pages = useList<Page>({
  doctype: 'GP Page',
  fields: ['name', 'creation', 'title', 'content', 'slug', 'project', 'team', 'modified', 'owner'],
  filters: props.listOptions.filters,
  orderBy: props.listOptions.orderBy,
  cacheKey: ['Pages', props.listOptions],
  staleOnError: true,
})

function getSpace(page: Page) {
  return useSpace(() => page.project).value
}

const getDropdownOptions = (page: Page) => [
  {
    label: 'Delete',
    icon: 'lucide-trash',
    condition: () => canDeleteContent(page, getSpace(page), useSessionUser()),
    onClick: () => {
      dialog.danger({
        title: 'Delete Page',
        message: 'Are you sure you want to delete this page?',
        onConfirm: () => pages.delete.submit({ name: page.name }),
      })
    },
  },
]
</script>
