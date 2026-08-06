<template>
  <FileUploader
    :fileTypes="fileTypes"
    :uploadArgs="uploadArgs"
    :validateFile="validateFile"
    @success="(file: UploadedFile) => emit('success', file)"
    @failure="(error: unknown) => emit('failure', error)"
  >
    <template #default="slotProps">
      <slot v-bind="slotProps" />
    </template>
  </FileUploader>
</template>

<script setup lang="ts">
/**
 * The only way Gameplan uploads an image from a file picker.
 *
 * It exists so privacy, optimization and accepted file types are decided once per
 * kind of image (see `utils/imageUpload.ts`) rather than at each call site. `kind`
 * is required and there is no `uploadArgs` escape hatch, so a new upload site
 * cannot quietly inherit whichever default its upload primitive happens to have.
 */
import { computed } from 'vue'
import { FileUploader, type FileUploaderSlotProps, type UploadedFile } from 'frappe-ui'
import {
  imageFileTypes,
  imageUploadArgs,
  validateImageFile,
  type ImageUploadKind,
} from '@/utils/imageUpload'

const props = defineProps<{
  kind: ImageUploadKind
}>()

const emit = defineEmits<{
  success: [file: UploadedFile]
  failure: [error: unknown]
}>()

defineSlots<{
  default(props: FileUploaderSlotProps): unknown
}>()

const fileTypes = computed(() => imageFileTypes(props.kind))
const uploadArgs = computed(() => imageUploadArgs(props.kind))

function validateFile(file: File) {
  return validateImageFile(props.kind, file)
}
</script>
