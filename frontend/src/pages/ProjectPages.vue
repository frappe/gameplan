<template>
  <div class="py-6">
    <div class="flex items-center justify-between">
      <div class="text-2xl font-semibold">Pages</div>
      <div class="flex items-center space-x-2">
        <Dropdown
          :options="[
            {
              label: 'Page Title',
              handler: () => (orderBy = 'title asc'),
            },
            {
              label: 'Date Updated',
              handler: () => (orderBy = 'modified desc'),
            },
            {
              label: 'Date Created',
              handler: () => (orderBy = 'creation desc'),
            },
          ]"
          placement="center"
        >
          <Button>
            <div class="flex items-center">
              <ArrowDownUp
                class="mr-1.5 h-4 w-4 leading-none"
                :stroke-width="1.5"
              />
              <span> Sort </span>
            </div>
          </Button>
        </Dropdown>
        <Button icon-left="plus" @click="newPage">New Page</Button>
      </div>
    </div>
    <div class="mt-5 grid grid-cols-1 gap-5 md:grid-cols-3 lg:grid-cols-4">
      <div
        class="text-base text-gray-600"
        v-if="!$resources.pages.data?.length"
      >
        No pages
      </div>
      <div class="relative" v-for="d in $resources.pages.data" :key="d.name">
        <div class="absolute top-0 right-0 p-3">
          <Dropdown
            :button="{
              icon: 'more-horizontal',
              label: 'Page Options',
              appearance: 'minimal',
            }"
            :options="[
              {
                label: 'Delete',
                icon: 'trash',
                handler: () => {
                  $dialog({
                    title: 'Delete Page',
                    message: 'Are you sure you want to delete this page?',
                    actions: [
                      {
                        label: 'Delete',
                        handler: ({ close }) => {
                          close()
                          return this.$resources.pages.delete.submit(d.name)
                        },
                        appearance: 'danger',
                      },
                      {
                        label: 'Cancel',
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
            name: 'ProjectPage',
            params: { pageId: d.name, slug: d.slug },
          }"
        >
          <section
            class="aspect-[37/50] cursor-pointer overflow-hidden rounded-xl border border-gray-50 p-3 shadow-md hover:shadow-lg"
          >
            <h1 class="text-lg font-medium leading-none">{{ d.title }}</h1>
            <div class="mt-1.5 text-xs leading-none text-gray-600">
              Updated {{ $dayjs(d.modified).fromNow() }}
            </div>
            <hr class="my-2 border-gray-100" />
            <div
              class="prose prose-sm pointer-events-none w-[200%] origin-top-left scale-[.55] prose-p:my-1 md:w-[250%] md:scale-[.39]"
              v-html="d.content"
            />
          </section>
        </router-link>
      </div>
    </div>
  </div>
</template>
<script>
import { Dropdown } from 'frappe-ui'
import ArrowDownUp from '~icons/lucide/arrow-up-down'

export default {
  name: 'ProjectPages',
  props: ['project'],
  components: { Dropdown, ArrowDownUp },
  data() {
    return {
      orderBy: 'modified desc',
    }
  },
  resources: {
    pages() {
      return {
        type: 'list',
        cache: ['Project Pages', this.project.doc.name],
        doctype: 'GP Page',
        fields: ['name', 'creation', 'title', 'content', 'slug', 'modified'],
        filters: { project: this.project.name },
        orderBy: this.orderBy,
        auto: true,
      }
    },
  },
  methods: {
    newPage() {
      this.$resources.pages.insert.submit(
        {
          project: this.project.name,
          title: 'Untitled',
          content: '',
        },
        {
          onSuccess(doc) {
            this.$router.push({
              name: 'ProjectPage',
              params: { pageId: doc.name },
            })
          },
        }
      )
    },
  },
}
</script>
<style scoped>
.sort-button:deep(.feather-minimize-2) {
  transform: rotate(15deg);
}
</style>
