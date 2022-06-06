<template>
  <div class="p-6" v-if="user && $resources.profile.doc">
    <div class="flex items-center">
      <h2 class="text-3xl font-bold text-gray-900">
        {{ $user(user).full_name }}
      </h2>

      <Input
        :disabled="$user().name != user"
        type="select"
        :options="[
          { label: 'Set Status', value: '', disabled: true },
          { label: 'Available', value: 'Available' },
          { label: 'Busy', value: 'Busy' },
          { label: 'Away', value: 'Away' },
        ]"
        v-model="$resources.profile.doc.status"
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
      :editable="$user().name === user"
      fieldname="readme"
      class="mt-6"
    />
  </div>
</template>
<script>
import { TextEditor, Popover } from 'frappe-ui'
import ReadmeEditor from '@/components/ReadmeEditor.vue'

export default {
  name: 'PeopleProfile',
  props: ['user'],
  components: { TextEditor, ReadmeEditor, Popover },
  resources: {
    profile() {
      return {
        type: 'document',
        doctype: 'Team User Profile',
        name: this.user,
        setValue: {
          onSuccess: () => {
            this.$getListResource('People').reload()
          },
        },
      }
    },
  },
}
</script>
