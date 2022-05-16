<template>
  <div class="p-6" v-if="update">
    <h2 class="text-xl font-semibold text-gray-900">{{ update.title }}</h2>

    <div class="grid items-center grid-cols-8 mt-3 gap-y-2">
      <div class="col-span-1">
        <label class="text-base text-gray-700">Status</label>
      </div>
      <div class="col-span-7">
        <Badge
          :color="
            { 'At Risk': 'yellow', 'On Track': 'green', 'Off Track': 'red' }[
              update.status
            ]
          "
        >
          {{ update.status }}
        </Badge>
      </div>
      <div class="col-span-1">
        <label class="text-base text-gray-700">Posted By</label>
      </div>
      <div class="flex items-center col-span-7 space-x-2">
        <UserInfo :email="update.owner" v-slot="{ user }">
          <Avatar
            :label="user.full_name"
            :imageURL="user.user_image"
            size="sm"
          />
          <span class="text-base text-gray-900">
            {{ user.full_name }}
          </span>
        </UserInfo>
      </div>
    </div>
    <div class="mt-2">
      <label class="text-base text-gray-700">Summary</label>
    </div>
    <TextEditor
      class="mt-1"
      editor-class="px-3 py-2 border rounded-lg max-w-[unset] min-h-[20rem]"
      :content="update.content"
      :editable="false"
    />
  </div>
</template>
<script>
import { Avatar, TextEditor } from 'frappe-ui'

export default {
  name: 'ProjectDetailUpdateView',
  props: ['project', 'updateId'],
  components: { TextEditor, Avatar },
  resources: {
    update() {
      return {
        type: 'document',
        doctype: 'Team Project Status Update',
        name: this.updateId,
      }
    },
  },
  computed: {
    update() {
      return this.$resources.update.doc
    },
  },
}
</script>
