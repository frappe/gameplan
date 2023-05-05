<template>
  <div class="py-6">
    <div class="flex items-center justify-between">
      <div class="text-2xl font-semibold">Pages</div>
      <div class="flex items-center space-x-2">
        <Dropdown
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
        >
          <Button>
            <span class="inline-flex items-center">
              <span> Sort </span>
            </span>
          </Button>
        </Dropdown>
        <Button icon-left="plus" @click="newPage">New Page</Button>
      </div>
    </div>
    <!-- <div>
      {{ $resources.pages.data }}
    </div> -->
    <div class="mt-4 grid grid-cols-4 gap-5">
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
        <router-link :to="{ name: 'ProjectPage', params: { pageId: d.name } }">
          <section
            class="aspect-[37/50] cursor-pointer overflow-hidden rounded-xl border border-gray-50 p-3 shadow-md hover:shadow-lg"
          >
            <h1 class="text-lg font-medium leading-none">{{ d.title }}</h1>
            <div class="mt-1.5 text-xs leading-none text-gray-600">
              Updated {{ $dayjs(d.modified).fromNow() }}
            </div>
            <hr class="my-2 border-gray-100" />
            <div
              class="prose prose-sm pointer-events-none w-[250%] origin-top-left scale-[.39] prose-p:my-1"
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
  resources: {
    pages() {
      return {
        type: 'list',
        doctype: 'GP Page',
        fields: ['name', 'creation', 'title', 'content', 'modified'],
        filters: { project: this.project.name },
        orderBy: 'modified desc',
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
