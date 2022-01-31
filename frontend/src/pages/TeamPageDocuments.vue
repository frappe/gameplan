<template>
  <div class="py-4 mx-auto max-w-main-content">
    <div class="grid grid-cols-6 gap-4">
      <button
        class="flex items-center justify-center border border-gray-400 border-dashed rounded-lg"
        @click="$resources.newDocument.submit()"
        :disabled="$resources.newDocument.loading"
      >
        <LoadingIndicator
          class="text-gray-600"
          v-if="$resources.newDocument.loading"
        />
        <div class="flex items-center space-x-0.5" v-else>
          <FeatherIcon name="plus" class="w-4 text-gray-600" />
          <span class="text-base leading-4 text-gray-600"> New document </span>
        </div>
      </button>
      <router-link
        custom
        v-for="document in $resources.documents.data"
        :key="document.name"
        :to="`/${team.name}/document/${document.name}/edit`"
        v-slot="{ href, navigate }"
      >
        <a
          :href="href"
          @click="navigate"
          class="flex flex-col h-24 p-4 bg-white rounded-lg shadow-sm hover:shadow"
        >
          <span
            :class="[
              document.title
                ? 'text-gray-900 font-semibold'
                : 'italic text-gray-700',
              'text-base',
            ]"
          >
            {{ document.title || 'Untitled' }}
          </span>
          <span class="mt-auto text-xs text-gray-500">
            {{ document.creation }}
          </span>
          <DropdownMenu
            :items="getDropdownItems(document)"
            class="flex items-center text-gray-400 rounded-full hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-100 focus:ring-blue-500"
          >
          </DropdownMenu>
        </a>
      </router-link>
    </div>
  </div>
</template>
<script>
import { LoadingIndicator } from 'frappe-ui'
import DropdownMenu from '@/components/DropdownMenu.vue'

export default {
  name: 'TeamPageDocuments',
  props: ['team'],
  components: {
    LoadingIndicator,
    DropdownMenu,
  },
  resources: {
    documents() {
      return {
        method: 'teams.api.get_documents',
        cache: ['team-documents', this.team.name],
        params: {
          team: this.team.name,
        },
        initialData: [],
        auto: true,
      }
    },
    newDocument() {
      return {
        method: 'teams.api.new_document',
        params: {
          team: this.team.name,
        },
        onSuccess(document) {
          this.$router.push(`/${this.team.name}/document/${document.name}/edit`)
        },
      }
    },
  },
  methods: {
    getDropdownItems(document) {
      return [
        {
          label: 'Home',
          route: `/${this.team.name}`,
        },
        {
          label: 'Delete',
          action: () => {
            this.deleteDocument(document)
          },
        },
      ]
    },
    deleteDocument(document) {
      console.log(document)
    },
  },
}
</script>
