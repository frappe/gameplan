<template>
  <div>
    <div class="flex items-center space-x-2">
      <h2 class="text-2xl font-bold text-gray-900">Important Links</h2>
      <Button
        icon="plus"
        label="New Link"
        @click="createNewLinkDialog = true"
      />
    </div>
    <div class="flex flex-col p-5 mt-5 bg-gray-100 rounded-xl">
      <div
        class="inline-flex items-center py-1 space-x-2 text-base font-medium text-gray-900 group"
        v-for="link in team.doc.links"
      >
        <div>
          <FeatherIcon
            name="arrow-up-right"
            class="w-3.5 h-3.5 text-gray-600 group-hover"
          />
        </div>
        <a
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="border-b border-transparent hover:border-gray-400"
        >
          {{ link.title || link.url }}
        </a>
        <button class="hidden p-1 bg-white rounded group-hover:block">
          <FeatherIcon name="edit-2" class="w-2.5 h-2.5 text-gray-900" />
        </button>
        <button class="hidden bg-white rounded group-hover:block p-0.5">
          <FeatherIcon name="x" class="w-3.5 h-3.5 text-gray-900" />
        </button>
      </div>
      <div v-if="!team.doc.links.length" class="text-base text-gray-600">
        Keep track of important links here. To add a link, click on the plus button above.
      </div>
    </div>
    <Dialog :options="{ title: 'Create Link' }" v-model="createNewLinkDialog">
      <template #body-content>
        <Input
          type="text"
          label="Link URL"
          placeholder="https://example.com"
          v-model="newLinkUrl"
        />
        <Input
          type="text"
          class="mt-2"
          label="Link Title"
          v-model="newLinkTitle"
        />
        <ErrorMessage
          class="mt-2"
          :message="$resources.createLink.error?.messages"
        />
      </template>
      <template #actions>
        <Button
          appearance="primary"
          @click="$resources.createLink.submit"
          :loading="$resources.createLink.loading"
        >
          Create
        </Button>
      </template>
    </Dialog>
  </div>
</template>
<script>
export default {
  name: 'TeamPageHomeLinks',
  props: ['team'],
  data() {
    return {
      createNewLinkDialog: false,
      newLinkUrl: '',
      newLinkTitle: '',
      undoables: [],
    }
  },
  resources: {
    createLink() {
      return {
        method: 'frappe.client.insert',
        params: {
          doc: {
            doctype: 'Team Link',
            parenttype: 'Team',
            parent: this.team.doc.name,
            parentfield: 'links',
            url: this.newLinkUrl,
            title: this.newLinkTitle,
          },
        },
        onSuccess() {
          this.createNewLinkDialog = false
          this.newLinkUrl = ''
          this.newLinkTitle = ''
          this.team.reload()
        },
      }
    },
    deleteLink() {
      return {
        method: 'frappe.client.delete',
        makeParams(link) {
          return {
            doctype: 'Team Link',
            name: link.name,
          }
        },
        onSuccess() {
          this.undoables.push({
            text: `Deleted link "${this.link.title || this.link.url}"`,
          })
          this.team.reload()
        },
      }
    },
  },
  deleteLink(link) {
    this.undoables.push({
      text: `Deleted link "${link.title || link.url}"`,
    })
  },
}
</script>
