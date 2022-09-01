<template>
  <div class="py-6" v-if="doc">
    <div class="flex items-center">
      <h2 class="text-3xl font-bold leading-7 text-gray-900">
        {{ $user(doc.user).full_name }}
      </h2>

      <Input
        :disabled="$user().name != doc.user"
        type="select"
        :options="[
          { label: 'Set Status', value: '', disabled: true },
          { label: 'Available', value: 'Available' },
          { label: 'Busy', value: 'Busy' },
          { label: 'Away', value: 'Away' },
        ]"
        v-model="doc.status"
        class="ml-2"
        @change="
          (value) =>
            $resources.profile.setValue.submit({
              status: value,
            })
        "
      />
    </div>
    <ReadmeEditor
      :resource="$resources.profile"
      :editable="$user().name === doc.user"
      fieldname="readme"
      class="mt-6"
      :placeholder="
        $user().name == doc.user
          ? 'Write a brief introduction of yourself...'
          : 'This person hasn\'t updated their introduction'
      "
    />
  </div>
</template>
<script>
import { TextEditor, Popover } from 'frappe-ui'
import ReadmeEditor from '@/components/ReadmeEditor.vue'

export default {
  name: 'PersonProfile',
  props: ['personId'],
  components: { TextEditor, ReadmeEditor, Popover },
  resources: {
    profile() {
      return {
        type: 'document',
        doctype: 'Team User Profile',
        name: this.personId,
      }
    },
  },
  computed: {
    doc() {
      return this.$resources.profile.doc
    },
  },
}
</script>
