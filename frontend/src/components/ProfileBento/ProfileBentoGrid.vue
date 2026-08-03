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
import { computed, nextTick, ref, useSlots } from 'vue'
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
  if (props.interactive) {
    classes.push('transition-[height,transform,width] duration-200 ease-out')
  }
  return classes
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
  moveFloatingCard(event)
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
  await nextTick()
}

function moveFloatingCard(event: PointerEvent) {
  let target = targetFromPoint(event.clientX, event.clientY)
  if (!target) return

  let nextCards = reorderedCards(target.cardId, target.position)
  if (sameOrder(nextCards, dragCards.value)) return

  dragCards.value = nextCards
}

function targetFromPoint(x: number, y: number) {
  let elements = document.elementsFromPoint(x, y)
  let cardElement = elements
    .map((element) => element.closest<HTMLElement>('[data-profile-card-wrapper="true"]'))
    .find((element) => element && element.dataset.profileCardId !== draggingCardId.value)
  if (!cardElement?.dataset.profileCardId) return null

  let rect = cardElement.getBoundingClientRect()
  let after = y > rect.top + rect.height / 2 || x > rect.left + rect.width / 2
  return {
    cardId: cardElement.dataset.profileCardId,
    position: after ? 'after' : 'before',
  } as const
}

function reorderedCards(targetCardId: string, position: 'after' | 'before') {
  let sourceIndex = dragCards.value.findIndex((card) => card.id === draggingCardId.value)
  let targetIndex = dragCards.value.findIndex((card) => card.id === targetCardId)
  if (sourceIndex === -1 || targetIndex === -1) return dragCards.value

  let nextCards = [...dragCards.value]
  let [movingCard] = nextCards.splice(sourceIndex, 1)
  let insertIndex = nextCards.findIndex((card) => card.id === targetCardId)
  if (position === 'after') {
    insertIndex += 1
  }
  nextCards.splice(insertIndex, 0, movingCard)
  return nextCards
}

function movedEnough(event: PointerEvent) {
  return Math.hypot(event.clientX - dragStart.value.x, event.clientY - dragStart.value.y) > 6
}

function cardElementFor(cardId: string) {
  return gridElement.value?.querySelector<HTMLElement>(`[data-profile-card-id="${cardId}"]`)
}

function sameOrder(first: ProfileBentoCardType[], second: ProfileBentoCardType[]) {
  return first.every((card, index) => card.id === second[index]?.id)
}

function resetDragState() {
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
