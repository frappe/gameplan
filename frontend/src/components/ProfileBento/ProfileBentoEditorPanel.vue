<template>
  <!--
    300px is the narrowest the panel can be at `md` and still fit the six size
    tabs on one line, which is why the cards lose a little padding there rather
    than the panel losing width.

    The whole panel is the editor for the selected card, so no click inside it
    may clear that selection. The marker sits on the root, not on each block, so
    a block added later cannot miss it.
  -->
  <aside class="hidden w-[300px] shrink-0 md:block lg:w-[320px]" data-profile-keep-selection>
    <!-- The negative margin buys the scrollbar and the focus rings room without
         moving the cards: the padding puts their edges back where they were. -->
    <div class="sticky top-5 -m-2 max-h-[calc(100vh-6rem)] space-y-4 overflow-y-auto p-2">
      <!-- The checklist is always here, and holds no state of its own: a row is
           ticked exactly when a card bound to that field is in the layout, so
           removing the card in the grid unticks the row. -->
      <div
        class="rounded-lg border border-outline-gray-2 bg-surface-base p-4 lg:p-5"
        data-profile-info-checklist
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

      <div v-if="card" class="rounded-lg border border-outline-gray-2 bg-surface-base p-4 lg:p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-medium text-ink-gray-9">{{ cardTypeLabel }}</h2>
          </div>
        </div>

        <div class="mt-4 space-y-3">
          <!-- Two save speeds on one screen, so say which is which. -->
          <p
            v-if="isBoundCard"
            class="text-sm leading-5 text-ink-gray-5"
            data-profile-bound-save-notice
          >
            {{ boundFieldTitle }} saves to your profile as soon as you change it — the layout still
            saves when you press Save.
          </p>

          <TextInput
            v-if="card.type !== 'Blank'"
            label="Title"
            class="w-full"
            :model-value="card.title"
            @update:model-value="updateTitle"
          >
          </TextInput>

          <!-- The value of a bound card lives on the profile, so it is edited
               here and written straight through, never onto the draft row. -->
          <template v-if="isBoundCard && fieldEditor">
            <template v-if="boundField === 'full_name'">
              <TextInput
                label="First name"
                class="w-full"
                data-profile-panel-field="first_name"
                :model-value="firstNameDraft"
                @update:model-value="firstNameDraft = $event"
                @blur="saveFullName"
                @keydown.enter.prevent="saveFullName"
              />
              <TextInput
                label="Last name"
                class="w-full"
                data-profile-panel-field="last_name"
                :model-value="lastNameDraft"
                @update:model-value="lastNameDraft = $event"
                @blur="saveFullName"
                @keydown.enter.prevent="saveFullName"
              />
            </template>

            <Textarea
              v-else-if="boundField === 'bio'"
              label="Bio"
              class="w-full"
              data-profile-panel-field="bio"
              :rows="4"
              :maxlength="profileBioLimit"
              :model-value="bioDraft"
              placeholder="Write a short bio"
              @update:model-value="bioDraft = $event"
              @blur="saveBio"
              @keydown.meta.enter.prevent="saveBio"
              @keydown.ctrl.enter.prevent="saveBio"
            >
              <template #description>{{ bioCharactersLeft }} characters left</template>
            </Textarea>

            <!-- `readme` is a rich text field; it does not fit an aside this narrow. -->
            <div v-else-if="boundField === 'readme'" class="space-y-1.5">
              <FormLabel label="About" size="md" />
              <Button icon-left="lucide-edit-2" @click="openAboutDialog">Edit about</Button>
            </div>

            <div v-else-if="boundImageField" class="space-y-1.5">
              <FormLabel :label="boundFieldTitle" size="md" />
              <div class="flex flex-wrap items-center gap-2">
                <FileUploader
                  :fileTypes="['image/png', 'image/jpeg']"
                  :uploadArgs="{ optimize: true }"
                  :validateFile="validateImageFile"
                  @success="uploadBoundImage"
                >
                  <template #default="{ progress, error, uploading, openFileSelector }">
                    <div class="relative">
                      <Button
                        icon-left="lucide-upload"
                        :loading="uploading || savingBoundField"
                        @click="openFileSelector"
                      >
                        {{ uploading ? `${progress}%` : boundImageUploadLabel }}
                      </Button>
                      <ErrorMessage
                        v-if="error"
                        class="absolute right-0 top-9 z-10 w-52 rounded border border-outline-gray-2 bg-surface-base p-2 shadow-sm"
                        :message="error"
                      />
                    </div>
                  </template>
                </FileUploader>
                <Button
                  v-if="hasImage"
                  icon-left="lucide-trash-2"
                  :disabled="savingBoundField"
                  @click="removeBoundImage"
                >
                  Remove
                </Button>
              </div>
            </div>
          </template>

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
        class="flex flex-col items-start gap-4 rounded-lg border border-dashed border-outline-gray-2 p-4 text-left lg:p-5"
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

    <ProfileAboutDialog
      v-model:open="showAboutDialog"
      :text="card?.text"
      :save="(value: string) => saveBoundField({ field: 'readme', value })"
    />
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
import ProfileAboutDialog from './ProfileAboutDialog.vue'
import {
  profileBioLimit,
  profileBoundFields,
  profileCardSizes,
  profileImageRenderingOptions,
  type ProfileBentoCard,
  type ProfileBoundField,
  type ProfileCardSize,
  type ProfileCardType,
  type ProfileFieldEditor,
  type ProfileFieldUpdate,
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
  /**
   * Writes a bound card's value to the profile. Unlike the layout, these land
   * immediately — they are not part of the draft the Save button commits.
   */
  fieldEditor?: ProfileFieldEditor
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
/** A custom card's text and image are part of the layout draft; a bound one's is not. */
const isCustomContentCard = computed(() => isContentCard.value && !isBoundCard.value)
const boundField = computed(() => {
  return isBoundCard.value ? (props.card?.field as ProfileBoundField | undefined) : undefined
})
const boundImageField = computed(() => {
  if (boundField.value === 'cover_image' || boundField.value === 'image') return boundField.value
  return undefined
})
const boundFieldTitle = computed(() => {
  // Used verbatim, not lowercased: "your about" reads badly where "your bio" does not.
  let spec = profileBoundFields.find((field) => field.field === props.card?.field)
  return spec?.title || props.card?.title || 'This field'
})
// The image controls name the field from the same spec the checklist reads, so
// one card cannot be called "Avatar" in one half of the panel and "Profile
// picture" in the other.
const boundImageUploadLabel = computed(() => {
  return `${hasImage.value ? 'Change' : 'Upload'} ${boundFieldTitle.value.toLowerCase()}`
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

const savingBoundField = ref(false)
const bioDraft = ref('')
const firstNameDraft = ref('')
const lastNameDraft = ref('')
const bioCharactersLeft = computed(() => profileBioLimit - bioDraft.value.length)

// The stored value only changes once a write lands and the profile reloads, so
// this never clobbers what is being typed.
watch(
  () => [props.card?.id, props.card?.text] as const,
  () => {
    bioDraft.value = props.card?.text || ''
  },
  { immediate: true },
)

watch(
  () => [props.fieldEditor?.firstName, props.fieldEditor?.lastName] as const,
  ([firstName, lastName]) => {
    firstNameDraft.value = firstName || ''
    lastNameDraft.value = lastName || ''
  },
  { immediate: true },
)

const showAboutDialog = ref(false)

function openAboutDialog() {
  showAboutDialog.value = true
}

function toggleBoundField(field: ProfileBoundField, ticked: unknown) {
  emit('toggleBoundField', field, Boolean(ticked))
}

async function saveBoundField(update: ProfileFieldUpdate) {
  if (!props.fieldEditor) throw new Error('Not editable')

  savingBoundField.value = true
  try {
    await props.fieldEditor.save(update)
  } finally {
    savingBoundField.value = false
  }
}

/**
 * The field editor already toasts a failure and the card keeps showing the
 * stored value, so the control just holds on to the draft the user typed.
 */
function commitBoundField(update: ProfileFieldUpdate) {
  saveBoundField(update).catch(() => {})
}

function saveBio() {
  if (savingBoundField.value || bioDraft.value === (props.card?.text || '')) return
  commitBoundField({ field: 'bio', value: bioDraft.value })
}

function saveFullName() {
  if (savingBoundField.value) return

  let firstName = firstNameDraft.value.trim()
  let lastName = lastNameDraft.value.trim()
  if (firstName === props.fieldEditor?.firstName && lastName === props.fieldEditor?.lastName) return
  commitBoundField({ field: 'full_name', firstName, lastName })
}

function uploadBoundImage(file: UploadedFile) {
  if (!boundImageField.value) return
  commitBoundField({ field: boundImageField.value, value: file.file_url })
}

function removeBoundImage() {
  if (!boundImageField.value) return
  commitBoundField({ field: boundImageField.value, value: '' })
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
