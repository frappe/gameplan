<template>
  <!-- The keydown handlers are `.self` on purpose: the card must only answer keys
       aimed at the card itself. Without it, the space handler's preventDefault
       swallows every space typed into an inline editor inside the card. -->
  <article
    ref="cardElement"
    class="group relative block w-full min-w-0 overflow-hidden rounded-7 text-left outline-none transition focus:outline-none focus-visible:outline-none"
    :class="[flow ? '' : 'h-full', cardChromeClass, cardShellClass, dragClass]"
    :style="rootStyle"
    :data-profile-card-id="card.id"
    :data-size="card.size"
    :role="interactive ? 'button' : undefined"
    :tabindex="interactive ? 0 : undefined"
    :aria-keyshortcuts="interactive ? moveKeyShortcuts : undefined"
    @click="selectCard"
    @keydown.enter.self="selectCard"
    @keydown.space.self.prevent="selectCard"
    @keydown.self="moveCard"
    @pointerdown="startPointerDrag"
  >
    <!-- One row rather than two buttons stacked on the same corner: the callers
         keep `interactive` and `canEdit` apart, but nothing here enforces it and
         a control hidden under another control is unreachable. The wider gap on
         a coarse pointer keeps the enlarged tap areas below from meeting. -->
    <div
      v-if="interactive || canEdit"
      class="absolute right-3 top-3 z-20 flex items-center gap-2 [@media(pointer:coarse)]:gap-5"
    >
      <Button
        v-if="interactive"
        :class="overlayButtonClass"
        variant="outline"
        size="xs"
        icon="lucide-x"
        :label="`Remove ${cardTypeLabel} card`"
        @click.stop="$emit('remove')"
        @pointerdown.stop
      />
      <!-- The owner edits a bound card's value elsewhere — settings, a dialog,
           or the customize page — so this only says where to go, it never edits. -->
      <Button
        v-if="canEdit"
        :class="overlayButtonClass"
        variant="outline"
        size="sm"
        icon="lucide-edit-2"
        :label="`Edit ${card.title}`"
        data-profile-card-edit
        @click.stop="$emit('edit')"
        @pointerdown.stop
      />
    </div>

    <div v-if="card.type === 'Blank'" class="h-full" />

    <!-- Centred, not top-left: the tile is a slot waiting to be filled, and an
         icon over a prompt reads as one at any size. The title is left out on
         purpose, since the checklist beside the canvas already names the card. -->
    <div
      v-else-if="showBoundEmptyPlaceholder"
      class="flex flex-col items-center justify-center gap-2 p-3 text-center sm:p-4"
      :class="flow ? 'min-h-[6.5rem]' : 'h-full'"
      data-profile-card-empty
    >
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"
      >
        <span class="size-4" :class="emptyState.icon" aria-hidden="true" />
      </span>
      <p class="text-sm font-medium leading-snug text-ink-gray-6">{{ emptyState.prompt }}</p>
    </div>

    <div
      v-else-if="showHtmlLayout"
      class="relative overflow-hidden"
      :class="flow ? '' : 'h-full'"
      :style="htmlViewportStyle"
    >
      <div ref="htmlStack" class="p-3 sm:p-4">
        <div class="flex items-center gap-1.5 pb-2 text-xs font-medium text-ink-gray-5 sm:text-sm">
          {{ card.title }}
        </div>
        <!-- `readme` is a Text Editor field: frappe sanitizes it on save. Same
             prose pair the editor and every other read-only render use. -->
        <div class="prose prose-v3 max-w-none" v-html="card.text" />
      </div>
      <template v-if="canExpand">
        <!-- The fade has to end in the card's own background, which dark mode
             changes (see `cardShellClass`) — `surface-base` there is the page
             behind the card, and would read as a dark band over the text. -->
        <div
          v-if="!expanded"
          class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-surface-base via-surface-base/85 to-transparent dark:from-surface-elevation-1 dark:via-surface-elevation-1/85"
          aria-hidden="true"
        />
        <Button
          class="absolute bottom-2 left-1/2 z-20 -translate-x-1/2"
          variant="ghost"
          size="sm"
          :label="expanded ? 'Show less' : 'Read more'"
          @click.stop="$emit('toggleExpanded')"
          @pointerdown.stop
        />
      </template>
    </div>

    <div
      v-else-if="showTextLayout"
      class="flex flex-col justify-between p-3 sm:p-4"
      :class="flow ? 'min-h-[6.5rem]' : 'h-full'"
    >
      <div class="flex items-center gap-1.5 pb-2 text-xs font-medium text-ink-gray-5 sm:text-sm">
        {{ card.title }}
        <span v-if="card.url" class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
      </div>
      <p :class="textClass">{{ textCardBody }}</p>
    </div>

    <div v-else class="h-full">
      <div ref="imageFrame" :class="imageFrameClass">
        <img
          v-if="imageUrl"
          :class="imageClass"
          :src="imageUrl"
          :alt="card.title"
          :style="imageStyle"
          @load="loadImageDimensions"
        />
        <ImageUploader
          v-else-if="interactive"
          class="block h-full"
          kind="bentoCard"
          @success="uploadImage"
        >
          <template #default="{ progress, uploading, error, openFileSelector }">
            <button
              type="button"
              class="flex h-full w-full flex-col items-center justify-center gap-2 p-3 text-center text-ink-gray-5 transition hover:bg-surface-gray-2 sm:p-4"
              :class="{ 'border border-outline-red-2 bg-surface-red-1': error }"
              @click.stop="openFileSelector"
              @pointerdown.stop
            >
              <div
                class="grid size-10 place-items-center rounded-6 border border-dashed bg-surface-base"
                :class="
                  error
                    ? 'border-outline-red-2 text-ink-red-2'
                    : 'border-outline-gray-3 text-ink-gray-6'
                "
              >
                <Spinner v-if="uploading" class="size-5" />
                <span
                  v-else
                  class="size-5"
                  :class="error ? 'lucide-image-off' : 'lucide-image-plus'"
                  aria-hidden="true"
                />
              </div>
              <div v-if="error" class="text-xs font-medium leading-snug text-ink-red-2 sm:text-sm">
                {{ error }}
              </div>
              <div v-else-if="showImageEmptyCopy" class="space-y-0.5">
                <div class="text-xs font-medium text-ink-gray-7 sm:text-sm">
                  {{ uploading ? `Uploading ${progress}%` : 'Add image' }}
                </div>
                <div class="text-xs leading-snug text-ink-gray-5 sm:text-sm">Click to upload</div>
              </div>
            </button>
          </template>
        </ImageUploader>
        <div
          v-else
          class="flex h-full flex-col items-center justify-center gap-2 p-3 text-center text-ink-gray-5 sm:p-4"
        >
          <div
            class="grid size-10 place-items-center rounded-6 border border-dashed border-outline-gray-3 bg-surface-base text-ink-gray-6"
          >
            <span class="lucide-image-plus size-5" aria-hidden="true" />
          </div>
          <div v-if="showImageEmptyCopy" class="space-y-0.5">
            <div class="text-xs font-medium text-ink-gray-7 sm:text-sm">Add image</div>
          </div>
        </div>
        <div class="absolute inset-x-0 top-0 p-3 sm:p-4" :class="imageCaptionClass">
          <div
            class="flex items-center gap-1.5 text-xs font-medium sm:text-sm"
            :class="imageTitleClass"
          >
            {{ card.title }}
            <span v-if="card.url" class="lucide-arrow-up-right size-3.5" aria-hidden="true" />
          </div>
        </div>
        <div
          v-if="imageCardBody"
          class="absolute inset-x-0 bottom-0 p-3 sm:p-4"
          :class="imageBodyClass"
        >
          <p :class="imageBodyTextClass">{{ imageCardBody }}</p>
        </div>
        <div
          v-if="repositioning && imageUrl"
          class="absolute inset-0 z-10 flex touch-none select-none items-center justify-center bg-surface-gray-9/35"
          :class="draggingImage ? 'cursor-grabbing' : 'cursor-grab'"
          @click.stop
          @pointerdown.stop="startImageReposition"
          @pointermove.stop="moveImageReposition"
          @pointerup.stop="endImageReposition"
          @pointercancel.stop="endImageReposition"
        >
          <div class="pointer-events-none text-center">
            <div class="text-sm font-medium text-ink-base sm:text-base">Drag image up or down</div>
            <div
              class="pointer-events-auto mt-3 flex items-center justify-center gap-2"
              data-image-reposition-control
              @pointerdown.stop
            >
              <Button @click.stop="saveImagePosition">Save</Button>
              <Button @click.stop="$emit('cancelImageReposition')">Cancel</Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <a
      v-if="!interactive && card.url && card.type !== 'Blank'"
      class="absolute inset-0"
      :href="card.url"
      target="_blank"
      rel="noreferrer"
      :aria-label="card.title"
    />
  </article>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useElementSize } from '@vueuse/core'
import { profileBoundFields, type ProfileBentoCard, type ProfileCardMove } from './types'
import {
  profileBentoFlowCollapsedHeight,
  profileBentoFlowImageMaxHeight,
} from './profileBentoLayout'
import { Button, Spinner } from 'frappe-ui'
import ImageUploader from '@/components/ImageUploader.vue'
import { useProfileImageReposition } from './useProfileImageReposition'

const props = defineProps<{
  card: ProfileBentoCard
  selected?: boolean
  interactive?: boolean
  /**
   * Rendered inside the customize editor. Kept separate from `interactive`,
   * which controls interaction (drag, select, remove) and is off for the drag
   * ghost — the ghost still has to look like the tile it was lifted from.
   */
  editor?: boolean
  draggable?: boolean
  dragging?: boolean
  repositioning?: boolean
  /** Single-column flow layout (mobile): the card sizes itself instead of being positioned. */
  flow?: boolean
  expanded?: boolean
  canExpand?: boolean
  /**
   * Show the edit affordance for the bound profile field this card displays. Set
   * only on the owner's own profile page — deliberately separate from
   * `interactive`, which means "customize page".
   */
  canEdit?: boolean
}>()

const emit = defineEmits<{
  cancelImageReposition: []
  edit: []
  move: [move: ProfileCardMove]
  pointerDown: [event: PointerEvent]
  remove: []
  saveImagePosition: [position: number]
  select: []
  toggleExpanded: []
  uploadImage: [fileUrl: string]
  'update:contentHeight': [height: number]
}>()

interface UploadedFile {
  file_url: string
}

const imageGradientClassBySize: Record<ProfileBentoCard['size'], string> = {
  '1x1': 'h-16',
  '1x2': 'h-20',
  '2x1': 'h-20',
  '2x2': 'h-28',
  '4x1': 'h-20',
  '4x2': 'h-32',
}

/**
 * Both overlay controls are revealed on hover, and a touch device never hovers —
 * yet they stay tappable, so the corner of a card fires a button nobody can see.
 * Anything that cannot hover therefore gets them permanently visible, and a
 * coarse pointer grows the tap area to ~44px with a transparent pseudo-element
 * so the button keeps its small drawn size on a desktop.
 */
const overlayButtonClass =
  'relative transition-opacity [@media(hover:hover)]:opacity-0 focus:opacity-100 group-hover:opacity-100 [@media(pointer:coarse)]:after:absolute [@media(pointer:coarse)]:after:-inset-2.5'

const cardElement = useTemplateRef<HTMLElement>('cardElement')
const htmlStack = ref<HTMLElement | null>(null)

/**
 * Light mode tells a card apart from the page with an outline; dark mode does it
 * with the card's own surface instead (see `cardShellClass`), so the resting
 * border only goes *transparent* — dropping the 1px would resize every card
 * between themes. Three states keep their border in both, because the border is
 * the only thing drawing them: selection, the dashed "nothing here yet"
 * placeholder, and an image card with no image. `hover:` still wins over
 * `dark:` — frappe-ui's dark variant is a zero-specificity `:where()` selector —
 * so the hover outline survives in dark without a `dark:hover:` restatement.
 */
const cardChromeClass = computed(() => {
  if (props.card.type === 'Blank') {
    if (!props.interactive) return 'border-0 ring-0 shadow-none'
    return props.selected
      ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
      : 'border border-transparent hover:bg-surface-gray-2'
  }
  if (showBoundEmptyPlaceholder.value) {
    return props.selected
      ? 'border border-dashed border-outline-gray-4 ring-2 ring-outline-gray-2'
      : 'border border-dashed border-outline-gray-3 hover:border-outline-gray-4'
  }
  if (showImageLayout.value) {
    if (!imageUrl.value && !props.selected) return 'border border-outline-gray-2'
    return props.selected
      ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
      : 'border border-transparent hover:border-outline-gray-3'
  }
  return props.selected
    ? 'border border-outline-gray-4 ring-2 ring-outline-gray-2'
    : 'border border-outline-gray-2 hover:border-outline-gray-3 dark:border-transparent'
})

// `surface-base` and `surface-elevation-1` are the same white in light mode, so
// the dark variant is what actually lifts the card off the page there. A Blank
// card is a spacer and stays invisible in both themes; an image card has no body
// of its own, but still needs the surface under the frames that do not fill it —
// an empty slot, or a `Fit`/`Natural` image narrower than its tile.
const cardShellClass = computed(() => {
  if (props.card.type === 'Blank') return ''
  if (showImageLayout.value) return 'dark:bg-surface-elevation-1'
  return 'bg-surface-base dark:bg-surface-elevation-1'
})

// `touch-none` only while the card is actually draggable: the reorder gesture is
// built on raw pointer events, and without it a touch device hands the gesture
// to the scroller first. The read-only profile page must keep scrolling, so it
// never gets it — and it has to survive the dragging branch too, since dropping
// `touch-action` mid-gesture is what lets the page scroll away under the drag.
const dragClass = computed(() => {
  if (!props.draggable) return ''
  if (props.dragging) return 'touch-none select-none cursor-grabbing opacity-20 scale-[0.98]'
  return 'touch-none select-none cursor-grab active:cursor-grabbing'
})

const textClass = computed(() => {
  return 'text-base font-medium leading-snug text-ink-gray-9 sm:text-xl'
})

const cardTypeLabel = computed(() => {
  return props.card.type === 'Blank' ? 'blank' : 'profile'
})

/**
 * Intentional, editor-only divergence from the profile page.
 *
 * A bound card whose profile field is empty is dropped from the layout entirely
 * on the profile page — no placeholder, identically for the owner and a visitor
 * (see `get_profile_bento_cards`). But a field ticked in the customize checklist
 * still needs a tile the user can select, resize and drag, so the editor shows a
 * muted placeholder for it — and only the editor.
 */
const showBoundEmptyPlaceholder = computed(() => {
  if (!props.editor || props.card.type === 'Blank') return false
  return props.card.source === 'field' && !props.card.text && !props.card.image
})

/**
 * The icon and prompt for an empty bound card. Falls back to the card's own
 * title for a bound field this build does not know about, which can only happen
 * against a newer server that added one.
 */
const emptyState = computed(() => {
  let spec = profileBoundFields.find((boundField) => boundField.field === props.card.field)
  if (spec) return { icon: spec.emptyIcon, prompt: spec.emptyPrompt }
  return { icon: 'lucide-plus', prompt: `Add ${props.card.title.toLowerCase()}` }
})

const showHtmlLayout = computed(() => {
  if (showBoundEmptyPlaceholder.value) return false
  return props.card.type !== 'Blank' && props.card.format === 'html'
})

const showImageLayout = computed(() => {
  if (showHtmlLayout.value || showBoundEmptyPlaceholder.value) return false
  return props.card.type === 'Image' || Boolean(imageUrl.value)
})

const showTextLayout = computed(() => {
  return !showImageLayout.value && !showHtmlLayout.value && !showBoundEmptyPlaceholder.value
})

const rootStyle = computed(() => {
  if (!props.flow || !showImageLayout.value) return undefined
  return {
    aspectRatio: String(flowAspectRatio.value),
    // The aspect ratio alone only caps portrait cards, so a full-width 1x1
    // (ratio 1) would render as a square the size of the phone screen.
    maxHeight: `${profileBentoFlowImageMaxHeight}px`,
  }
})

/**
 * In the single-column flow layout a card spans the full width, so a tall
 * declared size (1x2) would render as a ~2x-viewport-wide slab. Keep the
 * declared ratio but never let it go past 4:3 portrait.
 */
const flowAspectRatio = computed(() => {
  let [columns, rows] = props.card.size.split('x').map(Number)
  return Math.max(columns / rows, 3 / 4)
})

const htmlViewportStyle = computed(() => {
  if (!props.flow || props.expanded) return undefined
  return { maxHeight: `${profileBentoFlowCollapsedHeight}px` }
})

const imageFrameClass = computed(() => {
  if (imageRendering.value === 'Natural') {
    return 'relative grid h-full place-items-center bg-surface-gray-2'
  }

  return 'relative h-full'
})

const imageClass = computed(() => {
  return {
    Cover: 'h-full w-full object-cover',
    Fit: 'h-full w-full object-contain',
    Natural: 'max-h-full max-w-full object-contain',
  }[imageRendering.value]
})

const imageCaptionClass = computed(() => {
  if (!imageUrl.value) return ''
  if (imageRendering.value !== 'Cover') return ''
  return `bg-gradient-to-b from-surface-gray-7/50 to-transparent dark:from-surface-white/70 ${
    imageGradientClassBySize[props.card.size]
  }`
})

const imageTitleClass = computed(() => {
  if (!imageUrl.value) return 'text-ink-gray-6'
  if (imageRendering.value !== 'Cover') return 'text-ink-gray-6'
  return 'text-ink-gray-1'
})

const imageBodyClass = computed(() => {
  if (imageRendering.value !== 'Cover') return 'bg-surface-base/90'
  return 'bg-gradient-to-t from-surface-gray-7/75 to-transparent dark:from-surface-white/75'
})

const imageBodyTextClass = computed(() => {
  if (imageRendering.value !== 'Cover') return 'text-sm font-medium leading-snug text-ink-gray-9'
  return 'text-sm font-medium leading-snug text-ink-white'
})

const showImageEmptyCopy = computed(() => {
  return props.card.size !== '1x1'
})

const imageRendering = computed(() => {
  return props.card.imageRendering || 'Cover'
})

const imageUrl = computed(() => {
  return props.card.image
})

const {
  imageFrame,
  draggingImage,
  imageStyle,
  loadImageDimensions,
  startImageReposition,
  moveImageReposition,
  endImageReposition,
  saveImagePosition,
} = useProfileImageReposition({
  imageUrl: () => imageUrl.value,
  savedPosition: () => props.card.imagePosition,
  repositioning: () => Boolean(props.repositioning),
  onSave: (position) => emit('saveImagePosition', position),
})

const textCardBody = computed(() => {
  return props.card.text
})

const imageCardBody = computed(() => {
  return props.card.text?.trim()
})

function selectCard() {
  if (!props.interactive) return
  emit('select')
}

const moveKeys: Record<string, ProfileCardMove> = {
  ArrowLeft: 'earlier',
  ArrowRight: 'later',
  ArrowUp: 'rowUp',
  ArrowDown: 'rowDown',
}

const moveKeyShortcuts = Object.keys(moveKeys).join(' ')

/**
 * Reorder from the keyboard, the alternative to dragging that WCAG 2.5.7 asks
 * for.
 *
 * The arrows are taken bare. Only a focused card ever sees them, and the
 * handler is `.self`, so this claims them for exactly as long as a card is the
 * thing being operated: everywhere else on the page they still scroll, and a
 * card's own inline editor still gets its own caret keys.
 *
 * A modifier held with the arrow is left alone rather than treated as the same
 * gesture, so the browser's Back, Forward and jump-to-end keep working from
 * here.
 */
function moveCard(event: KeyboardEvent) {
  if (!props.interactive) return
  if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return

  let move = moveKeys[event.key]
  if (!move) return

  // Otherwise the page scrolls under the card that just moved.
  event.preventDefault()
  emit('move', move)
}

function uploadImage(file: UploadedFile) {
  emit('uploadImage', file.file_url)
}

function startPointerDrag(event: PointerEvent) {
  if (!props.draggable || event.button !== 0) return

  // Focus has to be taken by hand here. The grid calls `preventDefault()` on
  // this event to own the gesture, and that also cancels the focus a press
  // would otherwise give the card — so clicking a card selected it while
  // leaving the keyboard pointed at whatever was focused before, and every
  // reorder key went nowhere. Tabbing to the card was the only way in, which is
  // not a way in at all.
  cardElement.value?.focus()
  emit('pointerDown', event)
}

// `htmlStack` is never height-constrained (its wrapper does the clipping), so
// this stays the card's natural content height whether it is collapsed or
// expanded — the grid needs a value that does not change as it grows the tile.
const { height: htmlStackHeight } = useElementSize(htmlStack)
watch(htmlStackHeight, (height) => {
  if (!showHtmlLayout.value || !height) return
  emit('update:contentHeight', height)
})
</script>
