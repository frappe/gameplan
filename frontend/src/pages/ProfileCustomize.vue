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
        <ProfileBentoGrid
          :cards="cards"
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
        :card="selectedCard"
        :text-characters-left="selectedTextCharactersLeft"
        :bound-fields="boundFieldsInDraft"
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
import { resolveProfileBoundValues } from '@/components/ProfileBento/profileBoundValues'
import { profileCardTypeOptions } from '@/components/ProfileBento/types'
import { useProfileBentoCustomization } from '@/components/ProfileBento/useProfileBentoCustomization'
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

/**
 * The owner's profile, read only so that ticking a field in the checklist can
 * preview the card's real value. The server still resolves every bound card on
 * read; nothing here is ever saved onto the layout.
 */
const profileResource = useDoc<GPUserProfile>({
  doctype: 'GP User Profile',
  name: () => sessionUser.user_profile || '',
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
} = useProfileBentoCustomization(profileBentoSource, {
  boundValues: () => resolveProfileBoundValues(profileResource.doc),
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
  // drive it (the editor panel, the add-card buttons). Everything else clears.
  if (event.target.closest('[data-profile-card-id], [data-profile-keep-selection]')) return
  selectedCardId.value = ''
}

function beginImageReposition() {
  if (!selectedCard.value || selectedCard.value.type === 'Blank' || !selectedCard.value.image)
    return
  repositioningCardId.value = selectedCard.value.id
}

function saveImagePosition(imagePosition: number) {
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
