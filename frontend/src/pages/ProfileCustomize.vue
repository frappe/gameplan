<template>
  <div class="min-h-full bg-surface-base">
    <PageHeader>
      <Breadcrumbs class="h-7" :items="profileCustomizeBreadcrumbs" />
      <div
        v-if="canCustomize && !isLoadingDraft"
        class="flex shrink-0 items-center gap-2"
        data-profile-keep-selection
      >
        <!-- The state of the saved layout belongs next to the button that
             changes it, not inside the profile-info checklist, which is about
             what the page shows rather than how it is stored. Before the first
             save these are two ends of one fact, so only one is ever on screen:
             the page is following the default, or it has a layout of its own
             that can be given up. -->
        <Tooltip
          v-if="isDefaultLayout"
          text="Once you save, your page keeps the layout you saved and stops following changes to the default."
        >
          <span class="text-sm text-ink-gray-5" data-profile-default-layout-notice>
            Default layout
          </span>
        </Tooltip>
        <Button
          v-else
          icon-left="lucide-rotate-ccw"
          data-profile-restore-default-layout
          :loading="isResetting"
          @click="restoreDefaultLayout"
        >
          Restore default
        </Button>
        <!-- One Save for the whole screen. The layout and the profile info the
             bound cards show are both edited here and both stay local until this
             is pressed, so splitting them across two buttons would only make the
             person guess which half of their work a press commits. -->
        <Button
          variant="solid"
          icon-left="lucide-save"
          data-profile-save
          :loading="isSaving"
          :disabled="!isDirty"
          @click="saveProfileChanges"
        >
          Save
        </Button>
      </div>
    </PageHeader>

    <!-- Customizing takes a canvas and an editor side by side, which does not fit
         below `md`. Rendering the message instead of the grid keeps the drag
         listeners off a screen that could never finish the job. -->
    <div
      v-if="!canCustomize"
      class="mx-auto w-full max-w-[1180px] px-4 py-12 sm:px-6"
      data-profile-customize-too-narrow
    >
      <h2 class="text-lg font-semibold text-ink-gray-9">Customizing needs a wider screen</h2>
      <p class="mt-2 max-w-md text-base leading-6 text-ink-gray-6">
        There is no room here for the canvas and the editor side by side. Open this page on a wider
        screen to change your profile layout.
      </p>
      <Button v-if="profileRoute" class="mt-4" :route="profileRoute">Back to profile</Button>
    </div>

    <div
      v-else-if="isLoadingDraft"
      class="mx-auto flex w-full max-w-[1180px] px-4 py-12 text-base text-ink-gray-5 sm:px-6"
    >
      Loading profile page...
    </div>

    <!-- The canvas rides the page scroll; the panel sticks and scrolls on its
         own, so the editor for the selected card stays put while the canvas
         moves under it. The vertical padding belongs to the canvas alone — the
         panel has to reach the top of the scroll region to stick flush against
         it, and carries its own padding inside its scroller. -->
    <div v-else class="mx-auto flex w-full max-w-[1180px] gap-6 px-4 sm:px-6">
      <main class="min-w-0 flex-1 py-6">
        <!-- Dragging is not available to everyone, so the way round it has to be
             findable rather than merely present. Above the canvas, because a
             layout taller than the screen would put it out of sight below. -->
        <p class="mb-4 text-sm leading-5 text-ink-gray-5" data-profile-keyboard-hint>
          Drag a card to move it, or select one and use the arrow keys: left and right move it one
          place, up and down move it a row.
        </p>

        <!-- No `editable-cards` here on purpose: on this canvas a click selects a
             card and a drag reorders it, so a per-card edit button would fight
             both gestures. Bound values are edited in the panel. -->
        <ProfileBentoGrid
          :cards="canvasCards"
          :selected-card-id="selectedCardId"
          interactive
          :repositioning-card-id="repositioningCardId"
          @cancel-image-reposition="repositioningCardId = ''"
          @remove="removeCard"
          @reorder="reorderCards"
          @save-image-position="saveImagePosition"
          @select="selectedCardId = $event"
          @upload-image="({ cardId, fileUrl }) => setCardImage(cardId, fileUrl)"
        />

        <p
          v-if="cards.length === 0"
          class="rounded-lg border border-dashed border-outline-gray-2 p-6 text-sm leading-5 text-ink-gray-6"
          data-profile-empty-layout-notice
        >
          Nothing is selected, so your profile page will be empty.
        </p>
      </main>

      <ProfileBentoEditorPanel
        :card="selectedCanvasCard"
        :text-characters-left="selectedTextCharactersLeft"
        :bound-fields="boundFieldsInDraft"
        :field-draft="fieldDraft.draft.value"
        @add-card="addCard"
        @clear-selection="selectedCardId = ''"
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
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { useEventListener, useMediaQuery } from '@vueuse/core'
import {
  PageHeader,
  Breadcrumbs,
  Button,
  dialog,
  toast,
  Tooltip,
  useDoc,
  usePageMeta,
} from 'frappe-ui'
import ProfileBentoEditorPanel from '@/components/ProfileBento/ProfileBentoEditorPanel.vue'
import ProfileBentoGrid from '@/components/ProfileBento/ProfileBentoGrid.vue'
import { createServerProfileBentoSource } from '@/components/ProfileBento/profileBentoSource'
import { applyProfileBoundValues } from '@/components/ProfileBento/profileBoundValues'
import { confirmRestoreDefaultLayout } from '@/components/ProfileBento/restoreDefaultLayout'
import { useProfileBentoCustomization } from '@/components/ProfileBento/useProfileBentoCustomization'
import { useProfileFieldDraft } from '@/components/ProfileBento/useProfileFieldDraft'
import { useProfileFieldEditing } from '@/components/ProfileBento/useProfileFieldEditing'
import { useSessionUser } from '@/data/users'
import { extractServerMessage } from '@/utils'
import { isPermissionError } from '@/utils/errorMessage'
import type { ProfileFieldValues } from '@/components/ProfileBento/types'
import type { GPUserProfile } from '@/types/doctypes'

const sessionUser = useSessionUser()
// The editor panel appears from `md` up; without it there is nothing to edit
// with, so the canvas is not offered at all below that.
const canCustomize = useMediaQuery('(min-width: 768px)')
const profileRoute = computed(() => {
  if (!sessionUser.user_profile) return undefined
  return { name: 'PersonProfileProfile', params: { personId: sessionUser.user_profile } }
})
const profileCustomizeBreadcrumbs = computed(() => [
  { label: 'People', route: { name: 'People' } },
  {
    label: sessionUser.full_name || 'Profile',
    route: profileRoute.value,
  },
  { label: 'Customize', route: { name: 'ProfileCustomize' }, isPageTitle: true },
])

interface ProfileMethods {
  setImage: (data: { image: string | null }) => void
  setCoverImagePosition: (data: { position: number }) => void
}

/**
 * The owner's profile. The canvas resolves every bound card against it, and the
 * panel's bound-field controls stage their edits against it. Nothing bound is
 * ever saved onto the layout; the server resolves it again on every read.
 */
const profileResource = useDoc<GPUserProfile, ProfileMethods>({
  doctype: 'GP User Profile',
  name: () => sessionUser.user_profile || '',
  methods: {
    setImage: 'set_image',
    setCoverImagePosition: 'set_cover_image_position',
  },
})

// This page is only ever your own profile, so editing is always enabled. No
// `onSaved` here: the field draft writes several fields in one go and re-reads
// once at the end rather than after each of them.
const fieldEditor = useProfileFieldEditing({
  profile: profileResource,
  userId: () => profileResource.doc?.user || '',
  enabled: () => true,
})

/** What the server holds for every bound field, before anything is staged. */
const storedFieldValues = computed<ProfileFieldValues>(() => {
  let profile = profileResource.doc
  return {
    bio: profile?.bio || '',
    readme: profile?.readme || '',
    image: profile?.image || '',
    cover_image: profile?.cover_image || '',
    cover_image_position: profile?.cover_image_position ?? 50,
    firstName: fieldEditor.value?.firstName || '',
    lastName: fieldEditor.value?.lastName || '',
  }
})

const fieldDraft = useProfileFieldDraft({
  editor: () => fieldEditor.value,
  stored: () => storedFieldValues.value,
  onSaved: () => profileResource.reload(),
})

const route = useRoute()
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
  isDirty: isLayoutDirty,
  isSaving: isLayoutSaving,
  isResetting,
  loadDraft,
  resetDraft,
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

/**
 * The profile as the canvas should show it: what the server holds, with the
 * staged edits laid over the top. Reading the document directly would show the
 * saved value back to someone who has just typed a new one.
 */
const previewProfile = computed(() => {
  let profile = profileResource.doc
  if (!profile) return profile

  let values = fieldDraft.draft.value.values
  return {
    ...profile,
    bio: values.bio,
    readme: values.readme,
    image: values.image,
    cover_image: values.cover_image,
    cover_image_position: values.cover_image_position,
    full_name: [values.firstName, values.lastName].filter(Boolean).join(' '),
  }
})

/** The layout draft with every bound card's value filled in for display. */
const canvasCards = computed(() => applyProfileBoundValues(cards.value, previewProfile.value))
const selectedCanvasCard = computed(() => {
  return canvasCards.value.find((card) => card.id === selectedCardId.value)
})
const isBoundCoverSelected = computed(() => {
  let card = selectedCanvasCard.value
  return card?.source === 'field' && card.field === 'cover_image'
})

// Two drafts, one set of unsaved changes: the layout and the bound values are
// edited on the same screen and committed by the same button, so everything that
// asks "is there anything to save" asks it once, about both.
const isDirty = computed(() => isLayoutDirty.value || fieldDraft.isDirty.value)
const isSaving = computed(() => isLayoutSaving.value || fieldDraft.isSaving.value)

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
    selectCardFromRoute()
  } finally {
    isLoadingDraft.value = false
  }
}

/**
 * `?field=cover_image` deep-links a bound card, so the edit button on the
 * profile page lands on the tile it came from instead of an unselected canvas.
 */
function selectCardFromRoute() {
  let field = route.query.field
  if (typeof field !== 'string') return

  let card = cards.value.find((item) => item.source === 'field' && item.field === field)
  if (card) selectedCardId.value = card.id
}

function handleCustomizeKeydown(event: KeyboardEvent) {
  if (isEditableTarget(event.target)) return

  if (event.key === 'Escape') {
    // A dialog the panel opened takes Escape for itself; closing it should not
    // also drop the selection the panel was editing.
    if (!selectedCardId.value || isDialogTarget(event.target)) return
    event.preventDefault()
    selectedCardId.value = ''
    return
  }

  // On Mac the "delete" key emits "Backspace"; "Delete" is the forward-delete.
  if (event.key !== 'Delete' && event.key !== 'Backspace') return
  if (event.metaKey || event.ctrlKey || event.altKey) return
  if (!selectedCard.value) return

  event.preventDefault()
  removeSelectedCard()
}

/**
 * Both drafts are local until Save, so a bound value typed into the panel is an
 * unsaved change exactly as a moved card is, and leaving with either one is worth
 * a question.
 */
onBeforeRouteLeave(() => {
  if (!isDirty.value) return true

  return new Promise<boolean>((resolve) => {
    // `confirm`, not `danger`: this screen stays on gray, with no red anywhere.
    dialog.confirm({
      title: 'Discard changes',
      message: 'Your profile has unsaved changes. Leaving now discards them.',
      confirmLabel: 'Discard changes',
      cancelLabel: 'Keep editing',
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
    })
  })
})

/**
 * The bound values first, then the layout.
 *
 * The layout is only written when it actually changed: saving it marks the
 * profile as customized, which is a one-way door out of the evolving default, and
 * editing a bio is no reason to walk through it.
 */
async function saveProfileChanges() {
  // A failed field write has already said so; the staged values stay put.
  if (!(await fieldDraft.save())) return

  if (isLayoutDirty.value) {
    try {
      await saveDraft()
    } catch (error) {
      toast.error(getSaveErrorMessage(error))
      return
    }
  }
  toast.success('Profile saved')
}

/**
 * Restoring discards the saved layout on the server, not just in the draft, so
 * it asks first — and it takes any unsaved layout edits with it, which the
 * leave-guard never gets a chance to ask about because nobody is leaving. Staged
 * profile info survives: it is not part of the layout, as the question says.
 */
function restoreDefaultLayout() {
  confirmRestoreDefaultLayout(resetDraft, { hasUnsavedChanges: isLayoutDirty.value })
}

function clearSelectionOnOutsideClick(event: MouseEvent) {
  if (!selectedCardId.value) return
  if (!(event.target instanceof HTMLElement)) return

  // Keep the selection for clicks on a card or on a region that drives it: the
  // editor panel's blocks and the header actions both carry the marker, and a
  // dialog the panel opened needs its own exemption because it is teleported out
  // of the aside. A scrollbar is nobody's idea of clicking away, and its thumb
  // sits outside the panel's blocks. Everything else clears.
  if (
    event.target.closest(
      '[data-profile-card-id], [data-profile-keep-selection], [role="dialog"], [data-scrollbarimpl]',
    )
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

function saveImagePosition(imagePosition: number) {
  // The bound cover's position belongs to the image, not to the layout, so it
  // goes onto the field draft rather than the draft row. Either way the drag ends
  // in a draft, and the page's Save is what writes it.
  if (isBoundCoverSelected.value) {
    fieldDraft.draft.value.stage({ field: 'cover_image_position', value: imagePosition })
  } else {
    updateSelectedCard({ imagePosition })
  }
  repositioningCardId.value = ''
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(
    target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]'),
  )
}

function isDialogTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('[role="dialog"]'))
}

function getSaveErrorMessage(error: unknown) {
  if (isPermissionError(error)) {
    return 'You do not have permission to save this profile layout'
  }
  return extractServerMessage(error) || 'Could not save profile layout'
}
</script>
