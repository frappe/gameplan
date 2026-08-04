<template>
  <!--
    300px is the narrowest the panel can be at `md` and still fit the six size
    tabs on one line, which is why the cards lose a little padding there rather
    than the panel losing width.
  -->
  <aside class="hidden w-[300px] shrink-0 md:block lg:w-[320px]">
    <!-- Sticky, so the canvas scrolls with the page underneath while the editor
         for the selected card stays where it was. It sits flush against the top
         of the scroll region — the vertical padding is inside the ScrollArea, so
         the panel is exactly as tall as the space it sticks in and the first
         card still has room to breathe.

         A definite height, not a cap: ScrollArea's viewport is `h-full`, which
         resolves to `auto` inside a box that only has a max-height, and then
         nothing scrolls at all. -->
    <div class="sticky top-0" :style="panelStyle">
      <!-- The negative margin buys the scrollbar and the focus rings room
           without moving the cards: the padding puts their edges back. -->
      <ScrollArea class="-mx-2 h-full" viewport-class="px-2 py-6">
        <!-- The panel is the editor for the selected card, so no click on it may
             clear that selection. The marker goes on the blocks rather than the
             aside, which is as tall as the column whatever it holds: on the root
             it also claimed the empty space below the last block, where a click
             means the same thing as a click on the page behind it.

             One element around all the blocks, so a block added later cannot
             miss it. -->
        <div class="space-y-4" data-profile-keep-selection>
          <!-- One thing at a time. A selected card takes the whole panel, so the
             editor for what was just clicked is at the top of it rather than
             below a checklist that is not being used at the time. -->
          <div
            v-if="card"
            class="rounded-lg border border-outline-gray-2 bg-surface-base p-4 lg:p-5"
            data-profile-card-editor
          >
            <div class="flex items-center gap-2">
              <Button
                variant="subtle"
                icon="lucide-arrow-left"
                aria-label="Back to profile info"
                data-profile-card-editor-back
                @click="$emit('clearSelection')"
              />
              <h2 class="min-w-0 truncate text-base font-medium text-ink-gray-9">{{ cardName }}</h2>
            </div>

            <div class="mt-4 space-y-3">
              <!-- Two save speeds on one screen, so say which is which. -->
              <p
                v-if="boundSpec"
                class="text-sm leading-5 text-ink-gray-5"
                data-profile-bound-save-notice
              >
                This saves to your profile right away. The layout saves when you press Save.
              </p>

              <!-- A bound card's value lives on the profile, so the editor writes
                 straight through and never onto the draft row. -->
              <component
                :is="profileBoundFieldEditors[boundSpec.editor]"
                v-if="boundSpec && fieldEditor"
                :spec="boundSpec"
                :card="card"
                :field-editor="fieldEditor"
              />

              <template v-if="isCustomContentCard">
                <Textarea
                  label="Text"
                  class="w-full"
                  :rows="4"
                  :model-value="card.text"
                  @update:model-value="$emit('updateText', $event)"
                >
                  <template #description>{{ textCharactersLeft }} characters left</template>
                </Textarea>
                <TextInput
                  label="URL"
                  class="w-full"
                  type="url"
                  :model-value="card.url"
                  placeholder="https://example.com"
                  @update:model-value="$emit('updateUrl', $event)"
                />
                <ProfileImageField
                  label="Image"
                  :has-image="hasImage"
                  :removable="false"
                  @upload="$emit('uploadImage', $event)"
                />
              </template>

              <TextInput
                v-if="card.type !== 'Blank'"
                label="Title"
                class="w-full"
                :model-value="card.title"
                @update:model-value="$emit('updateTitle', $event)"
              />

              <div class="space-y-1.5">
                <FormLabel label="Size" size="md" />
                <TabButtons
                  :buttons="profileCardSizeButtons"
                  :model-value="card.size"
                  @update:model-value="(size: ProfileCardSize) => $emit('updateSize', size)"
                />
              </div>

              <template v-if="hasImage">
                <div class="space-y-1.5">
                  <FormLabel label="Rendering" size="md" />
                  <TabButtons
                    :options="profileImageRenderingOptions"
                    :model-value="card.imageRendering || 'Cover'"
                    @update:model-value="
                      (value: ProfileImageRendering) => $emit('updateImageRendering', value)
                    "
                  />
                </div>
                <Button
                  v-if="canRepositionImage"
                  icon-left="lucide-move-vertical"
                  @click="$emit('repositionImage')"
                >
                  Reposition
                </Button>
              </template>
            </div>
          </div>

          <!-- Two sections of one box, not two boxes: picking profile info and
             adding a card are both "what goes on the page", and a gap between
             them would say they were separate decisions. -->
          <div v-else class="rounded-lg border border-outline-gray-2 bg-surface-base">
            <!-- The checklist holds no state of its own: a row is ticked exactly
               when a card bound to that field is in the layout, so removing the
               card in the grid unticks the row. -->
            <div class="p-4 lg:p-5" data-profile-info-checklist>
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
            </div>

            <div class="border-t border-outline-gray-2 p-4 lg:p-5">
              <h2 class="text-base font-medium text-ink-gray-9">Build with cards</h2>
              <p class="mt-1 text-sm leading-5 text-ink-gray-5">
                Add a card or spacer, or select an item on the canvas to edit it.
              </p>
              <div class="mt-4 flex items-center gap-2">
                <Button icon-left="lucide-square" @click="$emit('addCard', 'Card')">Card</Button>
                <Button icon-left="lucide-square-dashed" @click="$emit('addCard', 'Blank')">
                  Spacer
                </Button>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useElementSize } from '@vueuse/core'
import {
  activeScrollContainer,
  Button,
  Checkbox,
  FormLabel,
  ScrollArea,
  TabButtons,
  Textarea,
  TextInput,
} from 'frappe-ui'
import ProfileImageField from './ProfileImageField.vue'
import { profileBoundFieldEditors } from './boundFields'
import {
  profileBoundFields,
  profileCardSizes,
  profileImageRenderingOptions,
  type ProfileBentoCard,
  type ProfileBoundField,
  type ProfileCardSize,
  type ProfileCardType,
  type ProfileFieldEditor,
  type ProfileImageRendering,
} from './types'

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
}>()

const emit = defineEmits<{
  addCard: [type: ProfileCardType]
  clearSelection: []
  repositionImage: []
  toggleBoundField: [field: ProfileBoundField, ticked: boolean]
  uploadImage: [fileUrl: string]
  updateImageRendering: [value: ProfileImageRendering]
  updateSize: [value: ProfileCardSize]
  updateText: [value: string]
  updateTitle: [value: string]
  updateUrl: [value: string]
}>()

/**
 * The panel's height, measured off the shell's scroll element rather than the
 * viewport. The shell teleports the page header out of its scroll region, so
 * that element is exactly the box the sticky panel can occupy, and `100vh`
 * would overshoot it by the header and leave the last control unreachable.
 */
const { height: shellHeight } = useElementSize(activeScrollContainer)
const panelStyle = computed(() => {
  if (!shellHeight.value) return undefined
  return { height: `${shellHeight.value}px` }
})

const profileCardSizeButtons = profileCardSizes.map((size) => ({ label: size }))

const isContentCard = computed(() => Boolean(props.card) && props.card?.type !== 'Blank')
/** The spec of the profile field this card is bound to, if it is bound to one. */
const boundSpec = computed(() => {
  if (!isContentCard.value || props.card?.source !== 'field') return undefined
  return profileBoundFields.find((spec) => spec.field === props.card?.field)
})
/** A custom card's text and image are part of the layout draft; a bound one's is not. */
const isCustomContentCard = computed(() => isContentCard.value && !boundSpec.value)

// The field's own name, so one card cannot be called "Avatar" on the checklist
// and "Profile picture" in the editor. A custom card is whatever it was titled.
const cardName = computed(() => {
  if (props.card?.type === 'Blank') return 'Spacer'
  return boundSpec.value?.title || props.card?.title || 'Card'
})

const hasImage = computed(() => isContentCard.value && Boolean(props.card?.image))
const canRepositionImage = computed(() => {
  return hasImage.value && (props.card?.imageRendering || 'Cover') === 'Cover'
})

function toggleBoundField(field: ProfileBoundField, ticked: unknown) {
  emit('toggleBoundField', field, Boolean(ticked))
}
</script>
