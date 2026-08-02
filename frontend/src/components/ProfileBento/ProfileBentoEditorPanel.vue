<template>
  <aside class="hidden w-[320px] shrink-0 lg:block">
    <div class="sticky top-5 space-y-4">
      <!-- The checklist is always here, and holds no state of its own: a row is
           ticked exactly when a card bound to that field is in the layout, so
           removing the card in the grid unticks the row. -->
      <div
        class="rounded-lg border border-outline-gray-2 bg-surface-base p-5"
        data-profile-info-checklist
        data-profile-keep-selection
      >
        <h2 class="text-base font-medium text-ink-gray-9">Profile info</h2>
        <p class="mt-1 text-sm leading-5 text-ink-gray-5">
          Pick what your profile page shows. Each card stays in sync with your profile.
        </p>
        <!-- `Checkbox` is `inline-flex`, so the rows need an explicit column. -->
        <div class="mt-4 flex flex-col items-start gap-3">
          <Checkbox
            v-for="boundField in profileBoundFields"
            :key="boundField.field"
            :label="boundField.title"
            :model-value="boundFields.has(boundField.field)"
            :data-profile-bound-field="boundField.field"
            @update:model-value="toggleBoundField(boundField.field, $event)"
          />
        </div>
        <p
          v-if="isEmptyLayout"
          class="mt-4 border-t border-outline-gray-2 pt-3 text-sm leading-5 text-ink-gray-6"
          data-profile-empty-layout-notice
        >
          Nothing is selected, so your profile page will be empty.
        </p>
        <p
          v-if="isDefaultLayout"
          class="mt-4 border-t border-outline-gray-2 pt-3 text-sm leading-5 text-ink-gray-6"
          data-profile-default-layout-notice
        >
          This is the default layout. Once you save, your profile keeps the layout you saved and
          stops following changes to the default.
        </p>
      </div>

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
          <p v-if="isBoundCard" class="text-sm leading-5 text-ink-gray-5">
            This card shows your {{ boundFieldTitle }} straight from your profile. Change the value
            on your profile page or in Settings — it is never stored on the card.
          </p>

          <TextInput
            v-if="card.type !== 'Blank'"
            label="Title"
            class="w-full"
            :model-value="card.title"
            @update:model-value="updateTitle"
          >
          </TextInput>
          <Textarea
            v-if="isCustomContentCard"
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
            <div v-if="isCustomContentCard" class="flex items-center justify-between gap-3">
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
        class="flex flex-col items-start gap-4 rounded-lg border border-dashed border-outline-gray-2 p-5 text-left"
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
  Checkbox,
  ErrorMessage,
  FileUploader,
  FormLabel,
  TabButtons,
  Textarea,
  TextInput,
} from 'frappe-ui'
import {
  profileBoundFields,
  profileCardSizes,
  profileImageRenderingOptions,
  type ProfileBentoCard,
  type ProfileBoundField,
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
  /** Bound fields present in the layout. The checklist reads its ticks from this. */
  boundFields: Set<ProfileBoundField>
  /** True while the layout is still the computed default (nothing saved yet). */
  isDefaultLayout?: boolean
  /** True when the layout has no cards at all. */
  isEmptyLayout?: boolean
}>()

const emit = defineEmits<{
  addCard: [type: ProfileCardType]
  remove: []
  repositionImage: []
  toggleBoundField: [field: ProfileBoundField, ticked: boolean]
  uploadImage: [fileUrl: string]
  updateImageRendering: [value: ProfileImageRendering]
  updateSize: [value: ProfileCardSize]
  updateText: [value: string]
  updateTitle: [value: string]
  updateUrl: [value: string]
}>()

const profileCardSizeButtons = profileCardSizes.map((size) => ({ label: size }))
const isContentCard = computed(() => {
  return Boolean(props.card) && props.card?.type !== 'Blank'
})
const isBoundCard = computed(() => {
  return isContentCard.value && props.card?.source === 'field'
})
/**
 * A bound card's text and image come from the profile and are discarded on save,
 * so it gets no text box and no image upload — only layout controls.
 */
const isCustomContentCard = computed(() => isContentCard.value && !isBoundCard.value)
const boundFieldTitle = computed(() => {
  let spec = profileBoundFields.find((boundField) => boundField.field === props.card?.field)
  return (spec?.title || props.card?.title || 'profile info').toLowerCase()
})
const cardTypeLabel = computed(() => {
  if (props.card?.type === 'Blank') return 'Blank card'
  return isBoundCard.value ? 'Profile info card' : 'Profile card'
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

function toggleBoundField(field: ProfileBoundField, ticked: unknown) {
  emit('toggleBoundField', field, Boolean(ticked))
}

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
