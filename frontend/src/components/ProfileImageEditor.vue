<template>
  <div class="space-y-5">
    <AvatarCropper ref="cropper" :file="file" />

    <ErrorMessage :message="errorMessage" />

    <div class="flex items-center justify-between gap-3">
      <Button variant="ghost" @click="resetCrop">Reset</Button>
      <div class="flex items-center gap-2">
        <Button @click="cancelCrop">Cancel</Button>
        <Button variant="solid" :loading="saving" @click="saveCroppedImage">Save</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { Button, ErrorMessage, useFileUpload } from 'frappe-ui'
import AvatarCropper from './AvatarCropper.vue'
import { useSessionUser } from '@/data/users'

interface ProfileDoc {
  image?: string | null
  original_image?: string | null
  is_image_background_removed?: number
  image_background_color?: string | null
}

interface ResourceCall<TParams = void, TResult = unknown> {
  loading: boolean
  error?: Error | string | null
  submit: TParams extends void ? () => Promise<TResult> : (params: TParams) => Promise<TResult>
}

interface ProfileResource {
  // Mirrors useDoc's resource shape, where `doc` is null until the document loads.
  doc: ProfileDoc | null
  setImage: ResourceCall<{ image: string | null }>
}

const props = defineProps<{
  profile: ProfileResource
  file: File
}>()

const emit = defineEmits<{
  (event: 'done'): void
  (event: 'cancel'): void
}>()

const sessionUser = useSessionUser()
const upload = useFileUpload()
const cropper = useTemplateRef<InstanceType<typeof AvatarCropper>>('cropper')
const validationError = ref('')
const saving = computed(() => upload.state.uploading || props.profile.setImage.loading)
const errorMessage = computed(() => {
  return validationError.value || upload.state.error?.message || upload.state.error || ''
})

function resetCrop() {
  cropper.value?.resetCrop()
}

function cancelCrop() {
  emit('cancel')
}

async function saveCroppedImage() {
  if (saving.value) return

  let blob = await cropper.value?.getCroppedBlob()
  if (!blob) {
    validationError.value = 'Could not crop image'
    return
  }

  try {
    let croppedFile = new File([blob], getCroppedFileName(props.file), {
      type: 'image/jpeg',
    })
    // Explicitly private to match ProfileImageField, which writes the same avatar
    // through FileUploader. useFileUpload defaults to public and FileUploader
    // defaults to private, so an avatar's visibility followed whichever screen set
    // it last. `set_image` saves the profile, and that attaches the File.
    let file = await upload.upload(croppedFile, { optimize: true, private: true })
    await setUserImage(file.file_url)
    emit('done')
  } catch {
    if (!upload.state.error) validationError.value = 'Could not save profile photo'
  }
}

async function setUserImage(url: string | null) {
  await props.profile.setImage.submit({ image: url })
  if (props.profile.doc) {
    props.profile.doc.image = url
    props.profile.doc.is_image_background_removed = 0
    props.profile.doc.image_background_color = ''
    props.profile.doc.original_image = ''
  }
  sessionUser.user_image = url || ''
  sessionUser.is_image_background_removed = 0
  sessionUser.image_background_color = ''
}

function getCroppedFileName(file: File) {
  let name = file.name.replace(/\.[^.]+$/, '')
  return `${name || 'avatar'}-cropped.jpg`
}
</script>
