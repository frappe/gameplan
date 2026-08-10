<template>
  <div ref="grid" class="grid w-fit grid-cols-10 gap-1">
    <div
      v-for="(emoji, index) in quickReactionSlots"
      :key="index"
      data-emoji-cell
      class="group relative size-8 select-none"
      :class="[
        emoji ? 'touch-none' : '',
        isDraggingIndex(index) ? 'cursor-grabbing' : emoji ? 'cursor-grab' : '',
      ]"
      :style="getCellStyle(index)"
      @click.capture="onCellClickCapture"
      @pointerdown="emoji && onCellPointerDown($event, index)"
      @pointermove="onCellPointerMove"
      @pointerup="onCellPointerUp"
      @pointercancel="onCellPointerCancel"
    >
      <EmojiPicker
        side="bottom"
        align="start"
        @select="(newEmoji) => setQuickReactionEmojiAt(index, newEmoji)"
      >
        <template #trigger>
          <button
            v-if="emoji"
            type="button"
            class="flex size-8 items-center justify-center rounded-5 border border-outline-gray-1 bg-surface-base text-xl font-[emoji] hover:bg-surface-gray-2"
          >
            <img
              v-if="isImageEmoji(emoji)"
              :src="emoji"
              alt=""
              draggable="false"
              class="pointer-events-none size-4 object-contain"
            />
            <template v-else>{{ emoji }}</template>
          </button>
          <button
            v-else
            type="button"
            class="flex size-8 items-center justify-center rounded-5 border border-dashed border-outline-gray-2 text-ink-gray-4 hover:border-outline-gray-3 hover:bg-surface-gray-1 hover:text-ink-gray-6"
            aria-label="Add emoji"
          >
            <span class="lucide-plus size-4" aria-hidden="true" />
          </button>
        </template>
      </EmojiPicker>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, type CSSProperties } from 'vue'
import EmojiPicker from '@/components/EmojiPicker.vue'
import {
  moveQuickReactionEmoji,
  quickReactionSlots,
  setQuickReactionEmojiAt,
} from '@/data/reactionPreferences'
import { isImageEmoji } from '@/utils/emoji'

// --- Pointer drag reorder (grid-aware) -------------------------------------
// Mirrors the customize-sidebar interaction, but in 2D: cells are measured once
// at drag start, the target slot is the nearest cell center, and neighbours
// slide by the delta between their measured positions. A small movement
// threshold keeps a plain click free to open the emoji picker.

interface CellPosition {
  x: number
  y: number
}

interface DragState {
  pointerId: number
  sourceIndex: number
  targetIndex: number
  startX: number
  startY: number
  currentX: number
  currentY: number
  positions: CellPosition[]
  centers: CellPosition[]
}

const DRAG_THRESHOLD = 4
const grid = useTemplateRef<HTMLElement>('grid')
const pending = ref<{ index: number; pointerId: number; startX: number; startY: number } | null>(
  null,
)
const drag = ref<DragState | null>(null)
let suppressClick = false

function onCellPointerDown(event: PointerEvent, index: number) {
  if (event.button !== 0) return
  suppressClick = false
  pending.value = {
    index,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
  }
}

function onCellPointerMove(event: PointerEvent) {
  const active = drag.value
  if (active) {
    if (active.pointerId !== event.pointerId) return
    active.currentX = event.clientX
    active.currentY = event.clientY
    active.targetIndex = nearestCellIndex(active, event.clientX, event.clientY)
    return
  }

  const start = pending.value
  if (!start || start.pointerId !== event.pointerId) return
  if (Math.hypot(event.clientX - start.startX, event.clientY - start.startY) < DRAG_THRESHOLD)
    return

  const { positions, centers } = measureCells()
  drag.value = {
    pointerId: start.pointerId,
    sourceIndex: start.index,
    targetIndex: start.index,
    startX: start.startX,
    startY: start.startY,
    currentX: event.clientX,
    currentY: event.clientY,
    positions,
    centers,
  }
  pending.value = null
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onCellPointerUp(event: PointerEvent) {
  const active = drag.value
  if (active && active.pointerId === event.pointerId) {
    releaseCapture(event)
    if (active.targetIndex !== active.sourceIndex) {
      moveQuickReactionEmoji(active.sourceIndex, active.targetIndex)
    }
    drag.value = null
    suppressClick = true
    return
  }
  if (pending.value?.pointerId === event.pointerId) pending.value = null
}

function onCellPointerCancel(event: PointerEvent) {
  if (drag.value?.pointerId === event.pointerId) {
    releaseCapture(event)
    drag.value = null
  }
  if (pending.value?.pointerId === event.pointerId) pending.value = null
}

// The Popover trigger opens via reka's as-child click wiring. After a drag we
// must cancel that click before it reaches the trigger — capture phase runs
// before the trigger's own handler, so stopPropagation here suppresses it.
function onCellClickCapture(event: MouseEvent) {
  if (!suppressClick) return
  suppressClick = false
  event.stopPropagation()
  event.preventDefault()
}

function isDraggingIndex(index: number) {
  return drag.value?.sourceIndex === index
}

function getCellStyle(index: number): CSSProperties | undefined {
  const state = drag.value
  if (!state) return

  if (index === state.sourceIndex) {
    return {
      transform: `translate3d(${state.currentX - state.startX}px, ${
        state.currentY - state.startY
      }px, 0)`,
      transition: 'none',
      zIndex: 20,
    }
  }

  const ease = 'transform 120ms cubic-bezier(0.16, 1, 0.3, 1)'
  let slot = index
  if (
    state.sourceIndex < state.targetIndex &&
    index > state.sourceIndex &&
    index <= state.targetIndex
  ) {
    slot = index - 1
  } else if (
    state.sourceIndex > state.targetIndex &&
    index >= state.targetIndex &&
    index < state.sourceIndex
  ) {
    slot = index + 1
  }
  if (slot === index) return { transition: ease }

  const dx = state.positions[slot].x - state.positions[index].x
  const dy = state.positions[slot].y - state.positions[index].y
  return { transform: `translate3d(${dx}px, ${dy}px, 0)`, transition: ease }
}

function measureCells() {
  const positions: CellPosition[] = []
  const centers: CellPosition[] = []
  const cells = grid.value?.querySelectorAll<HTMLElement>('[data-emoji-cell]')
  cells?.forEach((cell) => {
    const rect = cell.getBoundingClientRect()
    positions.push({ x: rect.left, y: rect.top })
    centers.push({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
  })
  return { positions, centers }
}

function nearestCellIndex(state: DragState, x: number, y: number) {
  let nearest = state.sourceIndex
  let nearestDistance = Infinity
  state.centers.forEach((center, index) => {
    const distance = (center.x - x) ** 2 + (center.y - y) ** 2
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearest = index
    }
  })
  return nearest
}

function releaseCapture(event: PointerEvent) {
  const element = event.currentTarget as HTMLElement
  if (element.hasPointerCapture?.(event.pointerId)) {
    element.releasePointerCapture(event.pointerId)
  }
}
</script>
