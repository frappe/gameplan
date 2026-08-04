import { computed, nextTick, onUnmounted, ref, type Ref } from 'vue'
import { activeScrollContainer } from 'frappe-ui'
import { createProfileBentoLayout, type ProfileBentoLayoutRect } from './profileBentoLayout'
import type { ProfileBentoCard } from './types'

interface Point {
  x: number
  y: number
}

export interface ProfileBentoDragOptions {
  /** The committed order. The drag works on a copy and only publishes it on drop. */
  cards: () => ProfileBentoCard[]
  /** The packed grid, which every measurement is taken relative to. */
  gridElement: Ref<HTMLElement | null>
  gridWidth: Ref<number>
  gap: number
  columns: number
  /** An expanded card's row span, so the base layout matches what is on screen. */
  rowSpan: (card: ProfileBentoCard) => number | undefined
  enabled: () => boolean
  onDrop: (order: string[], cardId: string) => void
}

/** Pointer travel that separates a drag from a click. */
const dragThreshold = 6
// How near an edge of the scroll container starts an autoscroll, and the pixels
// per frame it runs at. The floor matters as much as the ceiling: entering the
// zone has to move the page at once, or the shallow end reads as a dead strip.
const autoScrollZone = 60
const autoScrollMinSpeed = 2
const autoScrollMaxSpeed = 18

/**
 * Drag one card of a packed bento grid into a new place in the order.
 *
 * The grid owns what a card looks like and where the packer puts it; this owns
 * the gesture — the floating copy under the pointer, the order the canvas
 * previews while the card is in the air, and the autoscroll that makes a layout
 * taller than the screen reachable in one go.
 */
export function useProfileBentoDrag(options: ProfileBentoDragOptions) {
  const draggingCardId = ref('')
  const pendingDragCardId = ref('')
  /** The previewed order, published to the grid only when the card is let go. */
  const dragCards = ref<ProfileBentoCard[]>([])
  const dragStart = ref<Point>({ x: 0, y: 0 })
  const dragPointer = ref<Point>({ x: 0, y: 0 })
  /** Where inside the card it was grabbed, so the ghost hangs off the pointer. */
  const dragOffset = ref<Point>({ x: 0, y: 0 })
  const dragSize = ref({ width: 0, height: 0 })
  let autoScrollFrame = 0

  const draggingCard = computed(() => {
    if (!draggingCardId.value) return null
    return options.cards().find((card) => card.id === draggingCardId.value) || null
  })

  const floatingCardStyle = computed(() => {
    return {
      left: `${dragPointer.value.x - dragOffset.value.x}px`,
      top: `${dragPointer.value.y - dragOffset.value.y}px`,
      width: `${dragSize.value.width}px`,
      height: `${dragSize.value.height}px`,
    }
  })

  /**
   * The layout a drag is measured against: every card except the one in hand.
   *
   * The live layout cannot answer "where does this point belong", because it
   * packs the order the drag is in the middle of choosing — hole and all.
   * Reading it would close a loop: the index decides the layout, and the layout
   * decides the index. Two neighbouring orders can each look correct from the
   * other's geometry, so the grid flips between them while the pointer barely
   * moves.
   *
   * Taking the dragged card out breaks the loop. What is left does not move for
   * the rest of the gesture, so the index becomes a plain function of where the
   * ghost is — the same point always gives the same answer, and re-asking costs
   * nothing.
   */
  const dragBaseLayout = computed(() => {
    if (!draggingCardId.value) return null

    let items = options
      .cards()
      .filter((card) => card.id !== draggingCardId.value)
      .map((card) => ({ id: card.id, size: card.size, rows: options.rowSpan(card) }))
    return createProfileBentoLayout(items, options.gridWidth.value, options.gap, options.columns)
  })

  function startPointerDrag(cardId: string, event: PointerEvent) {
    if (!options.enabled()) return

    event.preventDefault()
    pendingDragCardId.value = cardId
    dragStart.value = { x: event.clientX, y: event.clientY }
    dragPointer.value = { x: event.clientX, y: event.clientY }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    window.addEventListener('pointercancel', cancelPointerDrag)
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
      options.onDrop(
        dragCards.value.map((card) => card.id),
        draggingCardId.value,
      )
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
    dragCards.value = [...options.cards()]
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

    // `insertionIndex()` reads the grid's rect live, so re-running the reorder
    // is enough to follow the scroll. No pointer event is needed, and none is
    // coming.
    moveFloatingCard()
  }

  function stopAutoScroll() {
    cancelAnimationFrame(autoScrollFrame)
    autoScrollFrame = 0
  }

  /**
   * Pixels to scroll this frame: nothing outside the hot zones, and faster the
   * deeper into one the pointer is, so the edge of a zone is a crawl and the
   * edge of the screen is a sprint.
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
    // Capped, because past the edge of the container the depth keeps growing
    // with however far the pointer has left the window.
    let ratio = Math.min(depth, autoScrollZone) / autoScrollZone
    return autoScrollMinSpeed + ratio * (autoScrollMaxSpeed - autoScrollMinSpeed)
  }

  /**
   * Move the dragged card to the place its own middle reads as, in reading order.
   *
   * What the grid stores is a list; what it shows is a packed wall of tiles in
   * five sizes. Reordering is picking a place in that list, so the honest
   * question is "how many cards come before this point?" rather than "which card
   * is nearest it?" — the second one has to be translated into the first, and
   * the translation is where it went wrong.
   *
   * Nearest slot centre answered left-to-right well and top-to-bottom badly,
   * because a tile's centre is only representative when the tile is small.
   * Dragging the avatar down over About, which is four columns wide, left its
   * middle 300px from About's, so the drag had to reach halfway down a two-row
   * card before anything moved. Counting is immune: the moment the ghost's
   * middle clears a row, everything in that row counts, whatever shape it is.
   *
   * Counted against `dragBaseLayout`, it is also monotonic, which is the
   * property that makes a drag feel like it obeys you. Down and to the right
   * always means later in the list, up and to the left always means earlier.
   * Counting against the live layout was not: the answer moved the tiles the
   * next answer would be read from.
   */
  function moveFloatingCard() {
    let index = insertionIndex(floatingCardCenter())
    let sourceIndex = dragCards.value.findIndex((card) => card.id === draggingCardId.value)
    // Inserting a card back at the index it already holds is the whole array
    // over again, so this is also the "nothing changed" test — and the one that
    // makes calling this on every pointermove and every autoscroll frame free.
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
  function floatingCardCenter(): Point {
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
   * one — one `getBoundingClientRect` for the whole grid instead of a hit test
   * per pointermove.
   *
   * Counting is order-independent, so `dragBaseLayout` holding a different order
   * from `dragCards` does not matter. It holds the same cards, which is all the
   * question needs.
   */
  function insertionIndex(center: Point) {
    let layout = dragBaseLayout.value
    let origin = options.gridElement.value?.getBoundingClientRect()
    if (!layout || !origin) return -1

    // Slot rects are relative to the grid; the ghost's middle is in the
    // viewport. Reading the grid's own rect every time is also what follows an
    // autoscroll: the ghost holds still on screen while this origin travels
    // under it.
    let x = center.x - origin.left
    let y = center.y - origin.top

    let index = 0
    for (let [, rect] of layout.rects) {
      if (readsBefore(rect, x, y)) index += 1
    }
    return index
  }

  /**
   * Whether a slot reads before a point: on an earlier row, or to its left on
   * the same one.
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

  function movedEnough(event: PointerEvent) {
    let travelled = Math.hypot(
      event.clientX - dragStart.value.x,
      event.clientY - dragStart.value.y,
    )
    return travelled > dragThreshold
  }

  function cardElementFor(cardId: string) {
    return options.gridElement.value?.querySelector<HTMLElement>(
      `[data-profile-card-id="${cardId}"]`,
    )
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

  // The listeners live on `window`, so a component torn down mid-drag would
  // leave them behind along with the grabbing cursor on `body`.
  onUnmounted(() => {
    removePointerListeners()
    resetDragState()
  })

  return {
    /** Empty unless a card is in the air. */
    draggingCardId,
    /** The order to render while dragging, in place of the committed one. */
    dragCards,
    /** The card under the pointer, for the floating copy. */
    draggingCard,
    floatingCardStyle,
    startPointerDrag,
  }
}
