<template>
  <Dialog :options="{ title: 'New Space' }" v-model="show">
    <template #body-content>
      <p class="text-p-base text-ink-gray-7">
        Spaces keep discussions, tasks, and pages in one place. Use them to group by team, project
        or any topic.
      </p>
      <div class="mt-3 space-y-2">
        <div class="space-x-2 flex items-center w-full">
          <IconPicker v-model="newSpace.icon" v-slot="{ isOpen }">
            <Button>
              <template #icon>
                <span v-if="newSpace.icon">{{ newSpace.icon }}</span>
                <LucidePlus v-else class="h-4 w-4" />
              </template>
            </Button>
          </IconPicker>
          <TextInput
            class="w-full"
            placeholder="Space name"
            id="new-space-name"
            v-model="newSpace.doc.title"
          />
        </div>

        <div class="flex items-center space-x-2">
          <div class="w-7 h-7"></div>
          <div>
            <FormControl
              type="checkbox"
              label="Keep it private &mdash; Only visible to members"
              v-model="newSpace.doc.is_private"
            />
          </div>
        </div>
      </div>
      <div class="mt-4">
        <ErrorMessage :message="newSpace.error" />
      </div>
    </template>
    <template #actions>
      <div class="flex items-center space-x-2 justify-end">
        <Button>Cancel</Button>
        <Button variant="solid" @click="submit" :loading="newSpace.loading">Submit</Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { Dialog, ErrorMessage, FormControl, TextInput } from 'frappe-ui'
import IconPicker from './IconPicker.vue'
import { useNewDoc } from '@/data/newDoc'
import { projects } from '@/data/projects'

const show = defineModel<boolean>()
const newSpace = useNewDoc('GP Project', {
  title: '',
  icon: '',
  is_private: false,
})

function submit() {
  newSpace.submit().then(() => {
    // TODO: useNewDoc should automatically reload related resources
    projects.reload()
    show.value = false
  })
}
</script>
