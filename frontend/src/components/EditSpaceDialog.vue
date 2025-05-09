<template>
  <Dialog :options="{ title: 'Edit Space' }" v-model="show">
    <template #body-content>
      <div class="mt-3 space-y-2" v-if="space">
        <div class="space-x-2 flex items-center w-full">
          <IconPicker v-model="space.icon" v-slot="{ isOpen }">
            <Button>
              <template #icon>
                <span v-if="space.icon">{{ space.icon }}</span>
                <LucidePlus v-else class="h-4 w-4" />
              </template>
            </Button>
          </IconPicker>
          <TextInput
            class="w-full"
            placeholder="Space name"
            v-model="space.title"
            v-focus:autoselect
          />
        </div>

        <div class="flex items-center space-x-2">
          <div class="w-7 h-7"></div>
          <div>
            <FormControl
              type="checkbox"
              :label="
                space.is_private
                  ? 'Private &mdash; Only visible to members'
                  : 'Public &mdash; Visible to everyone'
              "
              v-model="space.is_private"
              disabled
            />
          </div>
        </div>
      </div>
      <div class="mt-4">
        <ErrorMessage :message="spaces.setValue.error" />
      </div>
    </template>
    <template #actions>
      <div class="flex items-center space-x-2 justify-end">
        <Button variant="solid" @click="submit" :loading="spaces.setValue.loading">Submit</Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { Dialog, ErrorMessage, FormControl, TextInput } from 'frappe-ui'
import IconPicker from './IconPicker.vue'
import { useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'
import { vFocus } from '@/directives'

const props = defineProps<{ spaceId: string }>()
const show = defineModel<boolean>()

const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

function submit() {
  spaces.setValue
    .submit({
      name: props.spaceId,
      title: space.value?.title,
      icon: space.value?.icon,
    })
    .then(() => {
      show.value = false
    })
}
</script>
