<template>
  <div class="space-y-1.5">
    <FormLabel :label="label" size="md" />
    <div class="flex flex-wrap items-center gap-2">
      <!-- `private` is spelled out because the two components that write a profile
           image disagree by default: FileUploader uploads private, useFileUpload
           (in ProfileImageEditor) uploads public. Private is right as long as the
           File ends up attached to the doc, which is what makes it readable by
           everyone who can read that doc. -->
      <FileUploader
        :fileTypes="['image/png', 'image/jpeg']"
        :uploadArgs="{ optimize: true, private: true }"
        :validateFile="validateImageFile"
        @success="(file: UploadedFile) => emit('upload', file.file_url)"
      >
        <template #default="{ progress, error, uploading, openFileSelector }">
          <!-- Relative, so the error sits under the button that caused it instead
               of pushing every control below it down the panel. -->
          <div class="relative">
            <Button
              icon-left="lucide-upload"
              :loading="uploading || busy"
              @click="openFileSelector"
            >
              {{ uploading ? `${progress}%` : uploadLabel }}
            </Button>
            <ErrorMessage
              v-if="error"
              class="absolute right-0 top-9 z-10 w-52 rounded border border-outline-gray-2 bg-surface-base p-2 shadow-sm"
              :message="error"
            />
          </div>
        </template>
      </FileUploader>

      <slot name="actions" />

      <Button
        v-if="removable && hasImage"
        icon-left="lucide-trash-2"
        :disabled="busy"
        @click="emit('remove')"
      >
        Remove
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, ErrorMessage, FileUploader, FormLabel } from 'frappe-ui'

interface UploadedFile {
  file_url: string
}

const props = withDefaults(
  defineProps<{
    label: string
    /** Names the thing being uploaded, so the button can say "Change avatar". */
    subject?: string
    hasImage?: boolean
    /** A write is in flight elsewhere, so the buttons should not start another. */
    busy?: boolean
    removable?: boolean
  }>(),
  { removable: true },
)

const emit = defineEmits<{
  upload: [fileUrl: string]
  remove: []
}>()

// "Change" rather than "Upload" once there is something to replace, so the
// button says what pressing it will do rather than what it accepts.
const uploadLabel = computed(() => {
  let verb = props.hasImage ? 'Change' : 'Upload'
  return props.subject ? `${verb} ${props.subject.toLowerCase()}` : verb
})

function validateImageFile(file: File) {
  let extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !['png', 'jpg', 'jpeg'].includes(extension)) {
    return 'Only PNG and JPG images are allowed'
  }
}
</script>
