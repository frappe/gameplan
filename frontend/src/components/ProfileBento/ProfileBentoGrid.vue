<template>
  <div v-if="flowLayout" class="flex min-w-0 flex-col gap-3">
    <ProfileBentoCard
      v-for="card in flowCards"
      :key="card.id"
      flow
      :card="card"
      :can-edit="canEditCard(card)"
      :can-expand="canExpand(card)"
      :expanded="expandedCardIds.has(card.id)"
      @edit="$emit('edit', card)"
      @toggle-expanded="toggleExpanded(card.id)"
      @update:content-height="setCardContentHeight(card.id, $event)"
    />
  </div>

  <section v-else ref="gridElement" class="relative min-w-0" :style="gridStyle">
    <motion.div
      v-for="card in visibleCards"
      :key="card.id"
      :data-profile-card-id="card.id"
      data-profile-card-wrapper="true"
      :class="cardWrapperClass"
      :style="cardLayoutStyle(card)"
    >
      <ProfileBentoCard
        :card="card"
        :draggable="interactive"
        :dragging="draggingCardId === card.id"
        :selected="selectedCardId === card.id"
        :interactive="interactive"
        :editor="interactive"
        :repositioning="repositioningCardId === card.id"
        :can-edit="canEditCard(card)"
        :can-expand="canExpand(card)"
        :expanded="expandedCardIds.has(card.id)"
        @cancel-image-reposition="$emit('cancelImageReposition')"
        @edit="$emit('edit', card)"
        @pointer-down="startPointerDrag(card.id, $event)"
        @remove="$emit('remove', card.id)"
        @save-image-position="$emit('saveImagePosition', $event)"
        @select="$emit('select', card.id)"
        @toggle-expanded="toggleExpanded(card.id)"
        @update:content-height="setCardContentHeight(card.id, $event)"
        @upload-image="$emit('uploadImage', { cardId: card.id, fileUrl: $event })"
      />
    </motion.div>

    <motion.div
      v-if="hasAddCardSlot"
      data-profile-add-card-wrapper="true"
      :class="cardWrapperClass"
      :style="addCardLayoutStyle"
    >
      <slot />
    </motion.div>
  </section>

  <Teleport to="body">
    <motion.div
      v-if="draggingCard"
      class="pointer-events-none fixed z-[1000] opacity-95 shadow-xl"
      data-profile-drag-ghost="true"
      :style="floatingCardStyle"
      :initial="{ scale: 0.96, opacity: 0.85 }"
      :animate="{ scale: 1.03, opacity: 0.96 }"
      :transition="floatingTransition"
    >
      <ProfileBentoCard :card="draggingCard" :interactive="false" :editor="interactive" />
    </motion.div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, useSlots } from 'vue'
import { useElementSize, useMediaQuery } from '@vueuse/core'
import { motion } from 'motion-v'
import ProfileBentoCard from './ProfileBentoCard.vue'
import {
  createProfileBentoLayout,
  defaultProfileBentoColumns,
  profileBentoCardRows,
  profileBentoCellSize,
  profileBentoFlowCollapsedHeight,
  profileBentoHeightForRows,
  profileBentoRowsForHeight,
  type ProfileBentoLayoutRect,
} from './profileBentoLayout'
import type { ProfileBentoCard as ProfileBentoCardType } from './types'

const props = defineProps<{
  cards: ProfileBentoCardType[]
  selectedCardId?: string
  interactive?: boolean
  repositioningCardId?: string
  /**
   * Offer the owner an edit button on every bound card. Unrelated to
   * `interactive`, which means "customize page".
   */
  editableCards?: boolean
}>()

const emit = defineEmits<{
  cancelImageReposition: []
  edit: [card: ProfileBentoCardType]
  remove: [cardId: string]
  reorder: [cardIds: string[]]
  saveImagePosition: [position: number]
  select: [cardId: string]
  uploadImage: [payload: { cardId: string; fileUrl: string }]
}>()

const addCardLayoutId = '__profile-add-card__'
const gridGap = 12
// Room under an expanded card so the "Show less" control never sits on the text.
const expandedToggleHeight = 36
const slots = useSlots()
const draggingCardId = ref('')
const dragCards = ref<ProfileBentoCardType[]>([])
const dragStart = ref({ x: 0, y: 0 })
const dragPointer = ref({ x: 0, y: 0 })
const dragOffset = ref({ x: 0, y: 0 })
const dragSize = ref({ width: 0, height: 0 })
/** Where the ghost's middle was when the order last changed. See `travelledSinceReorder`. */
const lastReorderCenter = ref<{ x: number; y: number } | null>(null)
const reorderDeadBand = 12
const pendingDragCardId = ref('')
const gridElement = ref<HTMLElement | null>(null)
const { width: gridWidth } = useElementSize(gridElement)
const expandedCardIds = ref(new Set<string>())
const cardContentHeights = ref<Record<string, number>>({})

/** Only a bound card has a profile field to send the owner off to edit. */
function canEditCard(card: ProfileBentoCardType) {
  return Boolean(props.editableCards) && card.source === 'field'
}

// Below `sm` the packer is bypassed entirely: four columns of absolutely
// positioned squares do not survive a phone width. The customization grid keeps
// the packer at every width so drag-to-reorder stays available.
const isSmallScreen = useMediaQuery('(max-width: 639px)')
const flowLayout = computed(() => isSmallScreen.value && !props.interactive)

const floatingTransition = { type: 'spring', stiffness: 420, damping: 34, mass: 0.7 }

const visibleCards = computed(() => {
  return draggingCardId.value ? dragCards.value : props.cards
})

// A spacer only means something inside a packed grid.
const flowCards = computed(() => props.cards.filter((card) => card.type !== 'Blank'))

const cellSize = computed(() => {
  return profileBentoCellSize(gridWidth.value, gridGap, defaultProfileBentoColumns)
})

const hasAddCardSlot = computed(() => Boolean(slots.default))

const cardWrapperClass = computed(() => {
  let classes = ['absolute left-0 top-0 min-w-0']
  if (props.interactive && !layoutTransitionSuppressed.value) {
    classes.push('transition-[height,transform,width] duration-200 ease-out')
  }
  return classes
})

/**
 * Expanding an About card is a disclosure, not a move, so it lands instantly.
 *
 * The wrapper transition earns its keep during a drag, where tiles slide between
 * slots, so it is dropped for the toggle rather than deleted. Vue flushes the
 * flag and the new row span in one render, so the class is already gone from the
 * element in the same style recalculation that applies the new rect — which is
 * the whole trick: a transition cannot start on a property that is not
 * transitioned at the moment it changes.
 */
const layoutTransitionSuppressed = ref(false)
let layoutTransitionFrame = 0

function suppressLayoutTransition() {
  layoutTransitionSuppressed.value = true
  cancelAnimationFrame(layoutTransitionFrame)
  // Two frames: the first paints the new rect untransitioned, the second is
  // where it is safe to hand the transition back for the next drag.
  layoutTransitionFrame = requestAnimationFrame(() => {
    layoutTransitionFrame = requestAnimationFrame(() => {
      layoutTransitionSuppressed.value = false
    })
  })
}

onUnmounted(() => cancelAnimationFrame(layoutTransitionFrame))

const packedLayout = computed(() => {
  let items = visibleCards.value.map((card) => ({
    id: card.id,
    size: card.size,
    rows: expandedRowSpan(card),
  }))
  if (hasAddCardSlot.value) {
    items.push({ id: addCardLayoutId, size: '2x1', rows: undefined })
  }
  return createProfileBentoLayout(items, gridWidth.value, gridGap, defaultProfileBentoColumns)
})

/**
 * An expanded HTML card grows to the smallest whole number of rows that fits its
 * content, so the packer stays an integer grid and collapsing restores the exact
 * original layout. The cost is up to one cell of slack under the last line.
 */
function expandedRowSpan(card: ProfileBentoCardType) {
  if (card.format !== 'html' || !expandedCardIds.value.has(card.id)) return undefined
  let height = (cardContentHeights.value[card.id] || 0) + expandedToggleHeight
  return profileBentoRowsForHeight(height, cellSize.value, gridGap)
}

function collapsedHeight(card: ProfileBentoCardType) {
  if (flowLayout.value) return profileBentoFlowCollapsedHeight
  return profileBentoHeightForRows(profileBentoCardRows(card.size), cellSize.value, gridGap)
}

function canExpand(card: ProfileBentoCardType) {
  if (card.format !== 'html') return false
  let contentHeight = cardContentHeights.value[card.id] || 0
  // A couple of pixels of sub-pixel rounding is not "more to read".
  return contentHeight > collapsedHeight(card) + 4
}

function toggleExpanded(cardId: string) {
  suppressLayoutTransition()
  if (expandedCardIds.value.has(cardId)) {
    expandedCardIds.value.delete(cardId)
  } else {
    expandedCardIds.value.add(cardId)
  }
}

function setCardContentHeight(cardId: string, height: number) {
  cardContentHeights.value[cardId] = height
}

const gridStyle = computed(() => {
  return {
    height: `${packedLayout.value.height}px`,
  }
})

const addCardLayoutStyle = computed(() => {
  return rectStyle(packedLayout.value.rects.get(addCardLayoutId))
})

const draggingCard = computed(() => {
  if (!draggingCardId.value) return null
  return props.cards.find((card) => card.id === draggingCardId.value) || null
})

const floatingCardStyle = computed(() => {
  return {
    left: `${dragPointer.value.x - dragOffset.value.x}px`,
    top: `${dragPointer.value.y - dragOffset.value.y}px`,
    width: `${dragSize.value.width}px`,
    height: `${dragSize.value.height}px`,
  }
})

function startPointerDrag(cardId: string, event: PointerEvent) {
  if (!props.interactive) return

  event.preventDefault()
  pendingDragCardId.value = cardId
  dragStart.value = { x: event.clientX, y: event.clientY }
  dragPointer.value = { x: event.clientX, y: event.clientY }

  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('pointercancel', cancelPointerDrag)
}

function cardLayoutStyle(card: ProfileBentoCardType) {
  return rectStyle(packedLayout.value.rects.get(card.id))
}

async function handlePointerMove(event: PointerEvent) {
  event.preventDefault()
  dragPointer.value = { x: event.clientX, y: event.clientY }

  if (!draggingCardId.value && pendingDragCardId.value && movedEnough(event)) {
    await startFloatingDrag(pendingDragCardId.value, event)
  }

  if (!draggingCardId.value) return
  moveFloatingCard()
}

function handlePointerUp() {
  removePointerListeners()

  if (draggingCardId.value) {
    emit(
      'reorder',
      dragCards.value.map((card) => card.id),
    )
    emit('select', draggingCardId.value)
  }

  resetDragState()
}

function cancelPointerDrag() {
  removePointerListeners()
  resetDragState()
}

async function startFloatingDrag(cardId: string, event: PointerEvent) {
  let cardElement = cardElementFor(cardId)
  if (!cardElement) return

  let rect = cardElement.getBoundingClientRect()
  draggingCardId.value = cardId
  dragCards.value = [...props.cards]
  lastReorderCenter.value = null
  dragOffset.value = { x: event.clientX - rect.left, y: event.clientY - rect.top }
  dragSize.value = { width: rect.width, height: rect.height }
  document.body.classList.add('cursor-grabbing')
  await nextTick()
}

/**
 * Move the dragged card to the place its own middle reads as, in reading order.
 *
 * What the grid stores is a list; what it shows is a packed wall of tiles in
 * five sizes. Reordering is picking a place in that list, so the honest question
 * is "how many cards come before this point?" rather than "which card is nearest
 * it?" — the second one has to be translated into the first, and the translation
 * is where it went wrong.
 *
 * Nearest slot centre answered left-to-right well and top-to-bottom badly,
 * because a tile's centre is only representative when the tile is small. Dragging
 * the avatar down over About, which is four columns wide, left its middle 300px
 * from About's, so the drag had to reach halfway down a two-row card before
 * anything moved. Counting is immune: the moment the ghost's middle clears a
 * row, everything in that row counts, whatever shape it is.
 *
 * It is also monotonic, which is the property that makes a drag feel like it
 * obeys you. Down and to the right always means later in the list, up and to the
 * left always means earlier. Nearest-centre had no such guarantee.
 */
function moveFloatingCard() {
  let center = floatingCardCenter()
  if (!travelledSinceReorder(center)) return

  let index = insertionIndex(center)
  let sourceIndex = dragCards.value.findIndex((card) => card.id === draggingCardId.value)
  // Inserting a card back at the index it already holds is the whole array over
  // again, so this is also the "nothing changed" test.
  if (index === -1 || sourceIndex === -1 || index === sourceIndex) return

  let nextCards = dragCards.value.filter((card) => card.id !== draggingCardId.value)
  nextCards.splice(index, 0, dragCards.value[sourceIndex])

  dragCards.value = nextCards
  lastReorderCenter.value = center
}

/**
 * Where the ghost's middle sits, in the same viewport space as the pointer.
 *
 * The ghost hangs off the pointer by wherever the card was grabbed, so the
 * pointer is the wrong thing to measure with: a card held by a corner would
 * reorder half a card later than it looks like it should.
 */
function floatingCardCenter() {
  return {
    x: dragPointer.value.x - dragOffset.value.x + dragSize.value.width / 2,
    y: dragPointer.value.y - dragOffset.value.y + dragSize.value.height / 2,
  }
}

/**
 * Slot geometry comes from the packer, not from the DOM.
 *
 * The tiles are mid-transition for 200ms after every reorder, so their real
 * rects are wherever they happen to have slid to; the packer's are where they
 * are going. Measuring the destination is both the stable answer and the cheap
 * one — one `getBoundingClientRect` for the whole grid instead of a hit test per
 * pointermove.
 */
function insertionIndex(center: { x: number; y: number }) {
  let origin = gridElement.value?.getBoundingClientRect()
  if (!origin) return -1

  // Slot rects are relative to the grid; the ghost's middle is in the viewport.
  // The grid itself carries no size transition, so this rect is never mid-flight
  // the way a tile's is.
  let x = center.x - origin.left
  let y = center.y - origin.top

  let index = 0
  for (let card of dragCards.value) {
    // Counted among the others, never against itself: the dragged card's own
    // slot is the hole it came out of, and a hole cannot be before or after.
    if (card.id === draggingCardId.value) continue

    let rect = packedLayout.value.rects.get(card.id)
    if (rect && readsBefore(rect, x, y)) index += 1
  }
  return index
}

/**
 * Whether a slot reads before a point: on an earlier row, or to its left on the
 * same one.
 *
 * "Earlier row" is the slot's own edges rather than a row number, because rows
 * are not a thing the packer keeps — a two-row card shares a band with the
 * one-row cards beside it, and this reads that correctly without being told.
 */
function readsBefore(rect: ProfileBentoLayoutRect, x: number, y: number) {
  if (rect.top + rect.height <= y) return true
  if (rect.top >= y) return false
  return rect.left + rect.width / 2 < x
}

/**
 * A little real pointer travel is required between one reorder and the next.
 *
 * A reorder repacks every tile under the ghost, so the following pointermove is
 * counted against slots that have all moved. With cards of five sizes, two
 * neighbouring orders can each read as correct from the other's layout, and the
 * grid would then flicker between them while the pointer sits still. Sortable
 * calls this swap glitching and cures it by shrinking the swap zone; the same
 * cure here is a short dead band, small enough that no deliberate move notices.
 */
function travelledSinceReorder(center: { x: number; y: number }) {
  let last = lastReorderCenter.value
  if (!last) return true
  return Math.hypot(center.x - last.x, center.y - last.y) > reorderDeadBand
}

function movedEnough(event: PointerEvent) {
  return Math.hypot(event.clientX - dragStart.value.x, event.clientY - dragStart.value.y) > 6
}

function cardElementFor(cardId: string) {
  return gridElement.value?.querySelector<HTMLElement>(`[data-profile-card-id="${cardId}"]`)
}

function resetDragState() {
  draggingCardId.value = ''
  dragCards.value = []
  lastReorderCenter.value = null
  pendingDragCardId.value = ''
  document.body.classList.remove('cursor-grabbing')
}

function removePointerListeners() {
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('pointercancel', cancelPointerDrag)
}

function rectStyle(rect?: ProfileBentoLayoutRect) {
  if (!rect) {
    return {
      height: '0px',
      transform: 'translate3d(0, 0, 0)',
      width: '0px',
    }
  }

  return {
    height: `${rect.height}px`,
    transform: `translate3d(${rect.left}px, ${rect.top}px, 0)`,
    width: `${rect.width}px`,
  }
}
</script>
