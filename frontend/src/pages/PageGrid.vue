<template>
  <div class="grid grid-cols-1 gap-5 md:grid-cols-3 lg:grid-cols-4">
    <div class="text-base text-ink-gray-5" v-if="!$resources.pages.data?.length">No pages</div>
    <div class="relative" v-for="d in $resources.pages.data" :key="d.name">
      <div class="absolute right-0 top-0 p-3">
        <Dropdown
          :button="{
            icon: 'more-horizontal',
            label: 'Page Options',
            variant: 'ghost',
          }"
          :options="[
            {
              label: 'Delete',
              icon: 'trash',
              onClick: () => {
                $dialog({
                  title: 'Delete Page',
                  message: 'Are you sure you want to delete this page?',
                  actions: [
                    {
                      label: 'Delete',
                      onClick: (close) => {
                        close()
                        return $resources.pages.delete.submit(d.name)
                      },
                      variant: 'solid',
                      theme: 'red',
                    },
                  ],
                })
              },
            },
          ]"
          placement="right"
        />
      </div>
      <router-link
        :to="{
          name: d.project ? 'ProjectPage' : 'Page',
          params: {
            pageId: d.name,
            slug: d.slug,
            projectId: d.project,
            teamId: d.team,
          },
        }"
      >
        <section
          class="aspect-[37/50] cursor-pointer overflow-hidden rounded-md border border-gray-50 dark:border-outline-gray-1 p-3 shadow-lg transition-shadow hover:shadow-2xl"
        >
          <div class="overflow-hidden text-ellipsis whitespace-nowrap">
            <h1 class="text-lg font-semibold leading-none text-ink-gray-8">
              {{ d.title }}
            </h1>
            <div class="mt-1.5 flex items-center text-sm leading-none text-ink-gray-7">
              <div v-if="d.project">{{ projectTitle(d.project).value }} &middot;&nbsp;</div>
              <div>Updated {{ $dayjs(d.modified).fromNow() }}</div>
            </div>
            <hr class="my-2" />
            <div
              class="prose prose-sm pointer-events-none w-[200%] origin-top-left scale-[.55] prose-p:my-1 md:w-[250%] md:scale-[.39]"
              v-html="d.content"
            />
          </div>
        </section>
      </router-link>
    </div>
  </div>
</template>
<script>
import { projectTitle } from '@/utils/formatters'
import { Dropdown } from 'frappe-ui'

export default {
  name: 'PageGrid',
  props: ['listOptions'],
  resources: {
    pages() {
      return {
        type: 'list',
        cache: ['Pages', this.listOptions],
        doctype: 'GP Page',
        fields: ['name', 'creation', 'title', 'content', 'slug', 'project', 'team', 'modified'],
        filters: this.listOptions.filters,
        orderBy: this.listOptions.orderBy,
        auto: true,
      }
    },
  },
  methods: {
    projectTitle,
  },
  components: { Dropdown },
}
</script>
