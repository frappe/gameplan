<template>
  <div class="min-h-full bg-surface-base">
    <PageHeader>
      <Breadcrumbs class="h-7" :items="profileCustomizeBreadcrumbs" />
      <div
        v-if="!isLoadingDraft"
        class="flex shrink-0 items-center gap-2"
        data-profile-keep-selection
      >
        <Button
          v-for="option in profileCardTypeOptions"
          :key="option.type"
          :icon-left="option.icon"
          @click="addCard(option.type)"
        >
          {{ option.label }}
        </Button>
        <Button
          variant="solid"
          icon-left="lucide-save"
          data-profile-save-layout
          :loading="isSaving"
          :disabled="!isDirty"
          @click="saveProfileBentoDraft"
        >
          Save
        </Button>
      </div>
    </PageHeader>

    <div
      v-if="isLoadingDraft"
      class="mx-auto flex w-full max-w-[1180px] px-4 py-12 text-base text-ink-gray-5 sm:px-6"
    >
      Loading profile page...
    </div>

    <div v-else class="mx-auto flex w-full max-w-[1180px] gap-6 px-4 pb-32 pt-6 sm:px-6 sm:pb-40">
      <main class="min-w-0 flex-1">
        <!-- No `field-editor` here on purpose: on this canvas a click selects a
             card and a drag reorders it, so click-to-edit would fight both
             gestures. Bound values are edited in the panel. -->
        <ProfileBentoGrid
          :cards="canvasCards"
          :selected-card-id="selectedCardId"
          interactive
          :repositioning-card-id="repositioningCardId"
          show-size
          @cancel-image-reposition="repositioningCardId = ''"
          @remove="removeCard"
          @reorder="reorderCards"
          @save-image-position="saveImagePosition"
          @select="selectedCardId = $event"
          @upload-image="({ cardId, fileUrl }) => setCardImage(cardId, fileUrl)"
        />
      </main>

      <ProfileBentoEditorPanel
        :card="selectedCanvasCard"
        :text-characters-left="selectedTextCharactersLeft"
        :bound-fields="boundFieldsInDraft"
        :field-editor="fieldEditor"
        :is-default-layout="isDefaultLayout"
        :is-empty-layout="cards.length === 0"
        @add-card="addCard"
        @reposition-image="beginImageReposition"
        @toggle-bound-field="toggleBoundField"
        @upload-image="updateSelectedImage"
        @update-image-rendering="(imageRendering) => updateSelectedCard({ imageRendering })"
        @update-size="(size) => updateSelectedCard({ size })"
        @update-text="updateSelectedText"
        @update-title="(title) => updateSelectedCard({ title })"
        @update-url="(url) => updateSelectedCard({ url })"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useEventListener } from '@vueuse/core'
import { PageHeader, Breadcrumbs, Button, toast, useDoc, usePageMeta } from 'frappe-ui'
import ProfileBentoEditorPanel from '@/components/ProfileBento/ProfileBentoEditorPanel.vue'
import ProfileBentoGrid from '@/components/ProfileBento/ProfileBentoGrid.vue'
import { createServerProfileBentoSource } from '@/components/ProfileBento/profileBentoSource'
import { applyProfileBoundValues } from '@/components/ProfileBento/profileBoundValues'
import { profileCardTypeOptions } from '@/components/ProfileBento/types'
import { useProfileBentoCustomization } from '@/components/ProfileBento/useProfileBentoCustomization'
import { useProfileFieldEditing } from '@/components/ProfileBento/useProfileFieldEditing'
import { useSessionUser } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'

const sessionUser = useSessionUser()
const profileCustomizeBreadcrumbs = computed(() => [
  { label: 'People', route: { name: 'People' } },
  {
    label: sessionUser.full_name || 'Profile',
    route: sessionUser.user_profile
      ? { name: 'PersonProfileProfile', params: { personId: sessionUser.user_profile } }
      : undefined,
  },
  { label: 'Customize', route: { name: 'ProfileCustomize' }, isPageTitle: true },
])

interface ProfileMethods {
  setImage: (data: { image: string | null }) => void
  setCoverImagePosition: (data: { position: number }) => void
}

/**
 * The owner's profile. The canvas resolves every bound card against it, and the
 * panel's bound-field controls write straight to it. Nothing bound is ever saved
 * onto the layout; the server resolves it again on every read.
 */
const profileResource = useDoc<GPUserProfile, ProfileMethods>({
  doctype: 'GP User Profile',
  name: () => sessionUser.user_profile || '',
  methods: {
    setImage: 'set_image',
    setCoverImagePosition: 'set_cover_image_position',
  },
})

// This page is only ever your own profile, so editing is always enabled.
const fieldEditor = useProfileFieldEditing({
  profile: profileResource,
  userId: () => profileResource.doc?.user || '',
  enabled: () => true,
  onSaved: () => profileResource.reload(),
})

const profileBentoSource = createServerProfileBentoSource()
const isLoadingDraft = ref(true)
const repositioningCardId = ref('')
const {
  cards,
  boundFieldsInDraft,
  selectedCardId,
  selectedCard,
  selectedTextCharactersLeft,
  isDefaultLayout,
  isDirty,
  isSaving,
  loadDraft,
  saveDraft,
  addCard,
  toggleBoundField,
  reorderCards,
  removeCard,
  removeSelectedCard,
  updateSelectedCard,
  updateSelectedImage,
  setCardImage,
  updateSelectedText,
} = useProfileBentoCustomization(profileBentoSource)

/** The draft with every bound card's live profile value filled in for display. */
const canvasCards = computed(() => applyProfileBoundValues(cards.value, profileResource.doc))
const selectedCanvasCard = computed(() => {
  return canvasCards.value.find((card) => card.id === selectedCardId.value)
})
const isBoundCoverSelected = computed(() => {
  let card = selectedCanvasCard.value
  return card?.source === 'field' && card.field === 'cover_image'
})

onMounted(loadProfileBentoDraft)
useEventListener(window, 'keydown', handleCustomizeKeydown)
useEventListener(document, 'click', clearSelectionOnOutsideClick)

usePageMeta(() => {
  return {
    title: 'Customize Profile | Gameplan',
  }
})

async function loadProfileBentoDraft() {
  try {
    await loadDraft()
  } finally {
    isLoadingDraft.value = false
  }
}

function handleCustomizeKeydown(event: KeyboardEvent) {
  // On Mac the "delete" key emits "Backspace"; "Delete" is the forward-delete.
  if (event.key !== 'Delete' && event.key !== 'Backspace') return
  if (event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target)) return
  if (!selectedCard.value) return

  event.preventDefault()
  removeSelectedCard()
}

async function saveProfileBentoDraft() {
  try {
    await saveDraft()
    toast.success('Profile layout saved')
  } catch (error) {
    toast.error(getSaveErrorMessage(error))
  }
}

function clearSelectionOnOutsideClick(event: MouseEvent) {
  if (!selectedCardId.value) return
  if (!(event.target instanceof HTMLElement)) return

  // Keep the selection for clicks on a card or on regions that intentionally
  // drive it (the editor panel, the add-card buttons, a dialog the panel opened —
  // which is teleported out of the aside). Everything else clears.
  if (
    event.target.closest('[data-profile-card-id], [data-profile-keep-selection], [role="dialog"]')
  ) {
    return
  }
  selectedCardId.value = ''
}

function beginImageReposition() {
  let card = selectedCanvasCard.value
  if (!card || card.type === 'Blank' || !card.image) return
  repositioningCardId.value = card.id
}

async function saveImagePosition(imagePosition: number) {
  // The bound cover's position belongs to the image, not to the layout, so it is
  // written to the profile right away instead of into the draft row.
  if (isBoundCoverSelected.value) {
    if (!fieldEditor.value) return
    try {
      await fieldEditor.value.save({ field: 'cover_image_position', value: imagePosition })
    } catch {
      // Reported by the field editor; keep the overlay open so the drag survives.
      return
    }
    repositioningCardId.value = ''
    return
  }

  updateSelectedCard({ imagePosition })
  repositioningCardId.value = ''
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(
    target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]'),
  )
}

function getSaveErrorMessage(error: unknown) {
  if (error instanceof Error && error.exc_type === 'PermissionError') {
    return 'You do not have permission to save this profile layout'
  }

  let message = extractServerMessage(error)
  return message || 'Could not save profile layout'
}

/**
 * frappe-ui's `frappeRequest` puts the clean `frappe.throw()` text on the
 * error's `messages` array (parsed out of `_server_messages`). The plain
 * `message` is the noisy "<method> <ExcType>" string, so prefer `messages`.
 */
function extractServerMessage(error: unknown): string {
  if (error instanceof Error && Array.isArray((error as { messages?: unknown }).messages)) {
    let messages = (error as { messages: unknown[] }).messages.filter(
      (message): message is string => typeof message === 'string',
    )
    if (messages.length) return stripHtml(messages.join('\n'))
  }
  if (error instanceof Error && error.message) return stripHtml(error.message)
  return typeof error === 'string' ? error : ''
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').trim()
}
</script>
