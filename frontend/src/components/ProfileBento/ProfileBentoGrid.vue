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
        @move="moveCardWithKeyboard(card.id, $event)"
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

    <!-- A keyboard reorder slides the tiles and says nothing. Sighted users get
         the movement; this is the same news for everyone else. -->
    <p v-if="interactive" class="sr-only" aria-live="polite" data-profile-reorder-announcement>
      {{ reorderAnnouncement }}
    </p>
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
import { activeScrollContainer } from 'frappe-ui'
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
import type { ProfileBentoCard as ProfileBentoCardType, ProfileCardMove } from './types'

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
// How near an edge of the scroll container starts an autoscroll, and the pixels
// per frame it runs at. The floor matters as much as the ceiling: entering the
// zone has to move the page at once, or the shallow end reads as a dead strip.
const autoScrollZone = 60
const autoScrollMinSpeed = 2
const autoScrollMaxSpeed = 18
let autoScrollFrame = 0
const pendingDragCardId = ref('')
const gridElement = ref<HTMLElement | null>(null)
const { width: gridWidth } = useElementSize(gridElement)
const expandedCardIds = ref(new Set<string>())
const cardContentHeights = ref<Record<string, number>>({})
const reorderAnnouncement = ref('')

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

onUnmounted(() => {
  cancelAnimationFrame(layoutTransitionFrame)
  stopAutoScroll()
})

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
 * The layout a drag is measured against: every card except the one in hand.
 *
 * `packedLayout` cannot answer "where does this point belong", because it packs
 * the order the drag is in the middle of choosing — hole and all. Reading it
 * would close a loop: the index decides the layout, and the layout decides the
 * index. Two neighbouring orders can each look correct from the other's
 * geometry, so the grid flips between them while the pointer barely moves.
 *
 * Taking the dragged card out breaks the loop. What is left does not move for
 * the rest of the gesture, so the index becomes a plain function of where the
 * ghost is — the same point always gives the same answer, and re-asking costs
 * nothing.
 */
const dragBaseLayout = computed(() => {
  if (!draggingCardId.value) return null

  let items = props.cards
    .filter((card) => card.id !== draggingCardId.value)
    .map((card) => ({ id: card.id, size: card.size, rows: expandedRowSpan(card) }))
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
  dragOffset.value = { x: event.clientX - rect.left, y: event.clientY - rect.top }
  dragSize.value = { width: rect.width, height: rect.height }
  document.body.classList.add('cursor-grabbing')
  startAutoScroll()
  await nextTick()
}

/**
 * Keep scrolling while the card is held near an edge of the scroll container.
 *
 * This needs an animation frame loop of its own rather than a few lines in
 * `handlePointerMove`, because a pointer parked in the hot zone stops sending
 * events — and that is the whole case the feature exists for. A layout taller
 * than the viewport cannot be crossed in one gesture otherwise: the drag runs
 * out of screen with nothing left to aim at.
 *
 * The canvas rides the page scroll, so the element to move is the shell's
 * scroll container, not the grid. The ghost is `fixed` and driven by the
 * pointer, so it stays under the finger while the page travels underneath it.
 */
function startAutoScroll() {
  cancelAnimationFrame(autoScrollFrame)
  autoScrollFrame = requestAnimationFrame(autoScrollTick)
}

function autoScrollTick() {
  autoScrollFrame = requestAnimationFrame(autoScrollTick)

  let container = activeScrollContainer.value
  let velocity = autoScrollVelocity(container)
  if (!container || !velocity) return

  let before = container.scrollTop
  container.scrollTop = before + velocity
  // Already at the top or the bottom. Nothing moved, so nothing can have
  // changed places either.
  if (container.scrollTop === before) return

  // `insertionIndex()` reads the grid's rect live, so re-running the reorder is
  // enough to follow the scroll. No pointer event is needed, and none is coming.
  moveFloatingCard()
}

function stopAutoScroll() {
  cancelAnimationFrame(autoScrollFrame)
  autoScrollFrame = 0
}

/**
 * Pixels to scroll this frame: nothing outside the hot zones, and faster the
 * deeper into one the pointer is, so the edge of a zone is a crawl and the edge
 * of the screen is a sprint.
 */
function autoScrollVelocity(container: HTMLElement | null) {
  if (!container) return 0

  let bounds = container.getBoundingClientRect()
  let y = dragPointer.value.y
  let above = autoScrollZone - (y - bounds.top)
  let below = autoScrollZone - (bounds.bottom - y)

  if (above > 0) return -autoScrollSpeed(above)
  if (below > 0) return autoScrollSpeed(below)
  return 0
}

function autoScrollSpeed(depth: number) {
  // Capped, because past the edge of the container the depth keeps growing with
  // however far the pointer has left the window.
  let ratio = Math.min(depth, autoScrollZone) / autoScrollZone
  return autoScrollMinSpeed + ratio * (autoScrollMaxSpeed - autoScrollMinSpeed)
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
 * Counted against `dragBaseLayout`, it is also monotonic, which is the property
 * that makes a drag feel like it obeys you. Down and to the right always means
 * later in the list, up and to the left always means earlier. Counting against
 * the live layout was not: the answer moved the tiles the next answer would be
 * read from.
 */
function moveFloatingCard() {
  let index = insertionIndex(floatingCardCenter())
  let sourceIndex = dragCards.value.findIndex((card) => card.id === draggingCardId.value)
  // Inserting a card back at the index it already holds is the whole array over
  // again, so this is also the "nothing changed" test — and the one that makes
  // calling this on every pointermove and every autoscroll frame free.
  if (index === -1 || sourceIndex === -1 || index === sourceIndex) return

  let nextCards = dragCards.value.filter((card) => card.id !== draggingCardId.value)
  nextCards.splice(index, 0, dragCards.value[sourceIndex])

  dragCards.value = nextCards
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
 *
 * Counting is order-independent, so `dragBaseLayout` holding a different order
 * from `dragCards` does not matter. It holds the same cards, which is all the
 * question needs.
 */
function insertionIndex(center: { x: number; y: number }) {
  let layout = dragBaseLayout.value
  let origin = gridElement.value?.getBoundingClientRect()
  if (!layout || !origin) return -1

  // Slot rects are relative to the grid; the ghost's middle is in the viewport.
  // Reading the grid's own rect every time is also what follows an autoscroll:
  // the ghost holds still on screen while this origin travels under it.
  let x = center.x - origin.left
  let y = center.y - origin.top

  let index = 0
  for (let [, rect] of layout.rects) {
    if (readsBefore(rect, x, y)) index += 1
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
 * Reorder from the keyboard.
 *
 * Left and right name a step in the list directly. Up and down name a place on
 * screen, so they go the same way round as a drag: work out the point, then ask
 * the packer which index that point is.
 */
async function moveCardWithKeyboard(cardId: string, move: ProfileCardMove) {
  // A card can be dragged and typed at by two hands at once, and the drag holds
  // an order of its own that this would be editing behind its back.
  if (!props.interactive || draggingCardId.value) return

  let order = props.cards.map((card) => card.id)
  let from = order.indexOf(cardId)
  if (from === -1) return

  let to = keyboardMoveTarget(move, cardId, from, order.length)
  // Already at the end it was asked to go to.
  if (to === from) return

  order.splice(from, 1)
  order.splice(to, 0, cardId)
  emit('reorder', order)
  // Same as a drop: the card being moved is the one the panel should be editing.
  emit('select', cardId)
  announceMove(cardId, to, order.length)

  // The tiles re-render in the new list order, and a focused element moved in
  // the DOM loses the focus on the way. Nothing else would put it back, and the
  // next key press has nowhere to land without it.
  await nextTick()
  focusCard(cardId)
}

function keyboardMoveTarget(move: ProfileCardMove, cardId: string, from: number, total: number) {
  let step =
    move === 'rowUp' || move === 'rowDown'
      ? rowMoveTarget(move, cardId, from)
      : from + (move === 'earlier' ? -1 : 1)
  // Clamped rather than wrapped: a card that falls off one end and reappears at
  // the other is a surprise, and there is no undo here.
  return Math.min(Math.max(step, 0), total - 1)
}

/**
 * The index that puts the card in the row above or below the one it is in.
 *
 * Up goes to the head of the row above, down to the tail of the row below,
 * rather than to whatever sits in the same column. A packed row has no gaps to
 * aim at: the row above is full, or it would have swallowed a card already. So
 * the only places in it are its two ends, and picking the near end is the one
 * that always visibly moves the card. Aiming at a column instead would leave a
 * full-width card exactly where it was, since a four-column card can never sit
 * beside anything.
 */
function rowMoveTarget(move: ProfileCardMove, cardId: string, from: number) {
  let band = rowBand(cardId)
  if (!band) return from

  let targetRow = move === 'rowUp' ? band.first - 1 : band.last + 1
  if (targetRow < 0) return from

  // Without the moved card, so an index into this list is where it should be
  // spliced back in.
  let others = visibleCards.value.filter((card) => card.id !== cardId)
  let neighbours = others.filter((card) => coversRow(card.id, targetRow))
  // Nothing below the last row, and nothing to do about it.
  if (!neighbours.length) return from

  // The packer fills in reading order, so first in the list is leftmost in the row.
  let anchor = move === 'rowUp' ? neighbours[0] : neighbours[neighbours.length - 1]
  let at = others.findIndex((card) => card.id === anchor.id)
  return move === 'rowUp' ? at : at + 1
}

/**
 * The rows a card spans, as row numbers.
 *
 * The packer works in pixels and keeps no row index, but every row is one cell
 * plus one gap tall, so the number divides straight back out.
 */
function rowBand(cardId: string) {
  let rect = packedLayout.value.rects.get(cardId)
  let rowHeight = cellSize.value + gridGap
  if (!rect || rowHeight <= 0) return null

  return {
    first: Math.round(rect.top / rowHeight),
    last: Math.round((rect.top + rect.height - cellSize.value) / rowHeight),
  }
}

/** Whether a card is in this row, including a tall card passing through it. */
function coversRow(cardId: string, row: number) {
  let band = rowBand(cardId)
  return Boolean(band) && row >= band!.first && row <= band!.last
}

function announceMove(cardId: string, index: number, total: number) {
  let card = props.cards.find((item) => item.id === cardId)
  // A spacer has no title to announce, and "Card" is what the panel calls the
  // untitled rest.
  let name = card?.type === 'Blank' ? 'Spacer' : card?.title || 'Card'
  reorderAnnouncement.value = `${name} moved to position ${index + 1} of ${total}`
}

/** The card's own focusable element, not the wrapper `cardElementFor` measures. */
function focusCard(cardId: string) {
  gridElement.value
    ?.querySelector<HTMLElement>(`article[data-profile-card-id="${cardId}"]`)
    ?.focus()
}

function movedEnough(event: PointerEvent) {
  return Math.hypot(event.clientX - dragStart.value.x, event.clientY - dragStart.value.y) > 6
}

function cardElementFor(cardId: string) {
  return gridElement.value?.querySelector<HTMLElement>(`[data-profile-card-id="${cardId}"]`)
}

function resetDragState() {
  stopAutoScroll()
  draggingCardId.value = ''
  dragCards.value = []
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
