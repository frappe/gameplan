<template>
  <div>
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-bold">Attachments</h2>
      <Button icon-left="plus" @click="createNewAttachmentDialog = true">
        Add Attachment
      </Button>
    </div>
    <ul
      role="list"
      class="grid grid-cols-1 gap-4 py-4 mt-4 border-t border-gray-200 empty:py-0 sm:grid-cols-2"
    >
      <li
        v-for="link in project.doc.attachments"
        :key="link.name"
        class="flow-root"
      >
        <div
          class="relative flex items-center p-2 -m-2 space-x-4 overflow-hidden rounded-xl hover:bg-gray-50 focus-within:ring-2 focus-within:ring-blue-500 text-ellipsis"
        >
          <div
            class="flex items-center justify-center flex-shrink-0 w-10 h-10 bg-gray-100 rounded-lg"
          >
            <img
              v-if="link.image"
              :src="link.image"
              class="object-cover w-4 h-4"
            />
          </div>
          <div class="flex-1">
            <h3 class="text-base font-medium text-gray-900">
              <a :href="link.url" target="_blank" class="focus:outline-none">
                <span class="absolute inset-0" aria-hidden="true" />
                <span class="whitespace-nowrap">
                  {{ link.title }}
                </span>
              </a>
            </h3>
            <p class="mt-1 text-base text-gray-500 whitespace-nowrap">
              {{ link.url }}
            </p>
          </div>
        </div>
      </li>
    </ul>
    <div
      class="flex flex-col items-center justify-center py-8"
      v-if="project.doc.attachments.length === 0"
    >
      <FeatherIcon name="folder-plus" class="w-6 h-6 text-gray-500" />
      <span class="mt-2 text-base text-gray-800"> No attachments </span>
    </div>
    <Dialog
      :options="{ title: 'Add Attachment' }"
      v-model="createNewAttachmentDialog"
    >
      <template #body-content>
        <div class="space-y-4">
          <Input
            type="text"
            label="Type or paste any web URL"
            placeholder="docs.example.com"
            v-model="url"
          />
          <Input
            type="text"
            label="Title (optional)"
            placeholder="Project Documentation"
            v-model="title"
          />
        </div>
        <ErrorMessage class="mt-2" :message="project.addAttachment.error" />
      </template>
      <template #actions>
        <Button
          appearance="primary"
          @click="createAttachment()"
          :loading="project.addAttachment.loading"
        >
          Create
        </Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
import Dialog from 'frappe-ui/src/components/Dialog.vue'

export default {
  name: 'ProjectDetailOverviewLinks',
  props: ['project'],
  components: { Dialog },
  data() {
    return {
      url: '',
      title: '',
      createNewAttachmentDialog: false,
    }
  },
  methods: {
    createAttachment() {
      this.project.addAttachment.submit(
        { url: this.url, title: this.title },
        {
          onSuccess: () => {
            this.url = ''
            this.title = ''
            this.project.addAttachment.reset()
            this.createNewAttachmentDialog = false
            this.project.get.reload()
          },
        }
      )
    },
  },
}
</script>
