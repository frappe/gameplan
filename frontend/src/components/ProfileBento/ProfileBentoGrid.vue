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
import { useProfileBentoDrag } from './useProfileBentoDrag'
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
const gridElement = ref<HTMLElement | null>(null)
const { width: gridWidth } = useElementSize(gridElement)
const expandedCardIds = ref(new Set<string>())
const cardContentHeights = ref<Record<string, number>>({})
const reorderAnnouncement = ref('')

const { draggingCardId, dragCards, draggingCard, floatingCardStyle, startPointerDrag } =
  useProfileBentoDrag({
    cards: () => props.cards,
    gridElement,
    gridWidth,
    gap: gridGap,
    columns: defaultProfileBentoColumns,
    rowSpan: expandedRowSpan,
    enabled: () => Boolean(props.interactive),
    onDrop(order, cardId) {
      emit('reorder', order)
      // The card just put down is the one the panel should be editing.
      emit('select', cardId)
    },
  })

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

function cardLayoutStyle(card: ProfileBentoCardType) {
  return rectStyle(packedLayout.value.rects.get(card.id))
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

/** The card's own focusable element, not the wrapper the packer positions. */
function focusCard(cardId: string) {
  gridElement.value
    ?.querySelector<HTMLElement>(`article[data-profile-card-id="${cardId}"]`)
    ?.focus()
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
