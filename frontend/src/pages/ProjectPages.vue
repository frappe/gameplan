<template>
  <div class="py-6">
    <div class="flex items-center justify-between">
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
              <ArrowDownUp
                class="mr-1.5 h-4 w-4 leading-none"
                :stroke-width="1.5"
              />
              <span> Sort </span>
            </div>
          </Button>
        </Dropdown>
        <Button variant="solid" @click="newPage">
          <template #prefix><LucidePlus class="w-4" /></template>
          Add new
        </Button>
      </div>
    </div>
    <div class="mt-4.5 grid grid-cols-1 gap-5 md:grid-cols-3 lg:grid-cols-4">
      <div
        class="text-base text-gray-600"
        v-if="!$resources.pages.data?.length"
      >
        No pages
      </div>
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
                        onClick: ({ close }) => {
                          close()
                          return this.$resources.pages.delete.submit(d.name)
                        },
                        variant: 'solid',
                        theme: 'red',
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
            class="aspect-[37/50] cursor-pointer overflow-hidden rounded-md border transition-shadow border-gray-50 p-3 shadow-lg hover:shadow-2xl"
          >
            <h1 class="text-lg font-semibold leading-none">{{ d.title }}</h1>
            <div class="mt-1.5 text-base leading-none text-gray-700">
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
