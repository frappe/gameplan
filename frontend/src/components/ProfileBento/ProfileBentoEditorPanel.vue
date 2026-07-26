<template>
  <aside class="hidden w-[320px] shrink-0 lg:block">
    <div class="sticky top-5 space-y-4">
      <div
        v-if="card"
        class="rounded-lg border border-outline-gray-2 bg-surface-base p-5"
        data-profile-keep-selection
      >
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-medium text-ink-gray-9">{{ cardTypeLabel }}</h2>
          </div>
        </div>

        <div class="mt-4 space-y-3">
          <TextInput
            v-if="card.type !== 'Blank'"
            label="Title"
            class="w-full"
            :model-value="card.title"
            @update:model-value="updateTitle"
          >
          </TextInput>
          <Textarea
            v-if="isContentCard"
            label="Text"
            class="w-full"
            :rows="4"
            :model-value="card.text"
            @update:model-value="updateText"
          >
            <template #description>{{ textCharactersLeft }} characters left</template>
          </Textarea>
          <TextInput
            v-if="isContentCard"
            label="URL"
            class="w-full"
            type="url"
            :model-value="card.url"
            placeholder="https://example.com"
            @update:model-value="updateUrl"
          >
          </TextInput>

          <div class="space-y-1.5">
            <FormLabel label="Size" size="md" />
            <TabButtons
              :buttons="profileCardSizeButtons"
              :model-value="card.size"
              @update:model-value="updateSize"
            />
          </div>

          <div v-if="isContentCard">
            <div v-if="hasImage" class="mb-3 space-y-3">
              <div class="space-y-1.5">
                <FormLabel label="Rendering" size="md" />
                <TabButtons
                  :options="profileImageRenderingOptions"
                  :model-value="card.imageRendering || 'Cover'"
                  @update:model-value="updateImageRendering"
                />
              </div>
              <Button
                v-if="canRepositionImage"
                icon-left="lucide-move-vertical"
                @click="$emit('repositionImage')"
              >
                Reposition
              </Button>
            </div>
            <div class="flex items-center justify-between gap-3">
              <div class="space-y-1.5">
                <FormLabel label="Image" size="md" />
                <FileUploader
                  :fileTypes="['image/png', 'image/jpeg']"
                  :uploadArgs="{ optimize: true }"
                  :validateFile="validateImageFile"
                  @success="updateImage"
                >
                  <template #default="{ progress, error, uploading, openFileSelector }">
                    <div class="relative">
                      <Button
                        icon-left="lucide-upload"
                        :loading="uploading"
                        @click="openFileSelector"
                      >
                        {{ uploading ? `${progress}%` : imageUploadButtonLabel }}
                      </Button>
                      <ErrorMessage
                        v-if="error"
                        class="absolute right-0 top-9 z-10 w-52 rounded border border-outline-gray-2 bg-surface-base p-2 shadow-sm"
                        :message="error"
                      />
                    </div>
                  </template>
                </FileUploader>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-else
        class="flex min-h-40 flex-col items-start justify-center gap-4 rounded-lg border border-dashed border-outline-gray-2 p-5 text-left"
      >
        <div class="space-y-1">
          <div class="text-base font-medium text-ink-gray-7">Build with cards</div>
          <p class="text-sm leading-5 text-ink-gray-5">
            Add a card or spacer, or select an item on the canvas to edit it.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <Button icon-left="lucide-square" @click="$emit('addCard', 'Card')">Card</Button>
          <Button icon-left="lucide-square-dashed" @click="$emit('addCard', 'Blank')">
            Spacer
          </Button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Button,
  ErrorMessage,
  FileUploader,
  FormLabel,
  TabButtons,
  Textarea,
  TextInput,
} from 'frappe-ui'
import {
  profileCardSizes,
  profileImageRenderingOptions,
  type ProfileBentoCard,
  type ProfileCardSize,
  type ProfileCardType,
  type ProfileImageRendering,
} from './types'

interface UploadedFile {
  file_url: string
}

const props = defineProps<{
  card?: ProfileBentoCard
  textCharactersLeft: number
}>()

const emit = defineEmits<{
  addCard: [type: ProfileCardType]
  remove: []
  repositionImage: []
  uploadImage: [fileUrl: string]
  updateImageRendering: [value: ProfileImageRendering]
  updateSize: [value: ProfileCardSize]
  updateText: [value: string]
  updateTitle: [value: string]
  updateUrl: [value: string]
}>()

const editorLabelClass = 'text-base text-ink-gray-5'
const profileCardSizeButtons = profileCardSizes.map((size) => ({ label: size }))
const isContentCard = computed(() => {
  return Boolean(props.card) && props.card?.type !== 'Blank'
})
const cardTypeLabel = computed(() => {
  return props.card?.type === 'Blank' ? 'Blank card' : 'Profile card'
})
const hasImage = computed(() => {
  return isContentCard.value && Boolean(props.card?.image)
})
const canRepositionImage = computed(() => {
  return hasImage.value && (props.card?.imageRendering || 'Cover') === 'Cover'
})
const imageUploadButtonLabel = computed(() => {
  return hasImage.value ? 'Change image' : 'Upload'
})

function updateImage(file: UploadedFile) {
  emit('uploadImage', file.file_url)
}

function updateImageRendering(value: ProfileImageRendering) {
  emit('updateImageRendering', value)
}

function updateTitle(value: string) {
  emit('updateTitle', value)
}

function updateText(value: string) {
  emit('updateText', value)
}

function updateUrl(value: string) {
  emit('updateUrl', value)
}

function updateSize(value: ProfileCardSize) {
  emit('updateSize', value)
}

function validateImageFile(file: File) {
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !['png', 'jpg', 'jpeg'].includes(extension)) {
    return 'Only PNG and JPG images are allowed'
  }
}
</script>
