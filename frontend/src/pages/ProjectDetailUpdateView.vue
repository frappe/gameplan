<template>
  <div class="p-6" v-if="update">
    <div class="flex items-center space-x-4">
      <Avatar :label="$user().full_name" :imageURL="$user().user_image" />
      <div class="flex items-center w-full">
        <div>
          <span class="text-base text-gray-900">
            {{ $user().full_name }}
          </span>
          &middot;
          <span class="text-base text-gray-600">
            {{ $dayjs(update.creation).fromNow() }}
          </span>
        </div>
        <Badge
          class="ml-auto"
          :color="{
            green: update.status === 'On Track',
            red: update.status === 'Off Track',
            yellow: update.status === 'At Risk',
          }"
        >
          {{ update.status }}
        </Badge>
      </div>
    </div>
    <TextEditor
      class="mt-3"
      editor-class="max-w-[unset] min-h-[20rem] prose-sm"
      :content="content"
      :editable="false"
    />
  </div>
</template>
<script>
import { Avatar } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'

export default {
  name: 'ProjectDetailUpdateView',
  props: ['project', 'updateId'],
  components: { TextEditor, Avatar },
  resources: {
    update() {
      return {
        type: 'document',
        doctype: 'Team Project Discussion',
        name: this.updateId,
      }
    },
  },
  computed: {
    update() {
      return this.$resources.update.doc
    },
    content() {
      return `<h2>${this.update.title}</h2>${this.update.content}`
    }
  },
}
</script>
