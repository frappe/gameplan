<template>
  <div class="px-6 pt-8" v-if="$resources.user.doc">
    <h1 class="text-2xl font-semibold text-gray-900">Personal Settings</h1>
    <div class="grid grid-cols-2 gap-4 mt-6">
      <FileUploader
        class="col-span-2"
        @success="
          (file) =>
            $resources.user.setValue.submit({ user_image: file.file_url })
        "
      >
        <template v-slot="{ file, progress, uploading, openFileSelector }">
          <div class="flex items-center space-x-2">
            <Avatar
              :label="$resources.user.doc.full_name"
              :imageURL="$resources.user.doc.user_image"
            />
            <Button @click="openFileSelector" :loading="uploading">
              {{ uploading ? `Uploading ${progress}%` : 'Upload Image' }}
            </Button>
          </div>
        </template>
      </FileUploader>
      <Input
        label="First Name"
        type="text"
        v-model="$resources.user.doc.first_name"
      />
      <Input
        label="Last Name"
        type="text"
        v-model="$resources.user.doc.last_name"
      />
    </div>
    <div class="mt-6">
      <Button
        appearance="primary"
        :loading="$resources.user.setValue.loading"
        @click="
          () => {
            $resources.user.setValue.submit(
              {
                first_name: $resources.user.doc.first_name,
                last_name: $resources.user.doc.last_name,
              },
              {
                onSuccess: () => {
                  $getResource('user')?.reload()
                  $getResource([
                    'user_info',
                    $resources.user.doc.name,
                  ])?.reload()
                },
              }
            )
          }
        "
      >
        Save
      </Button>
    </div>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import { Avatar, FileUploader } from 'frappe-ui'
export default {
  name: 'PersonalSettings',
  components: {
    Avatar,
    Breadcrumbs,
    FileUploader,
  },
  resources: {
    user() {
      return {
        type: 'document',
        doctype: 'User',
        name: this.$user().name,
      }
    },
  },
  pageMeta() {
    return {
      title: 'Personal Settings',
      emoji: '⚙️',
    }
  },
}
</script>
