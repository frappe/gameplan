<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed z-20 -translate-x-1/2"
      :class="isCoarsePointer ? 'pt-7' : '-translate-y-full pb-1.5'"
      :style="{ left: `${position.x}px`, top: `${position.y}px` }"
    >
      <div class="rounded-5 border bg-surface-elevation-2 p-0.5 shadow-md">
        <Button
          variant="ghost"
          icon-left="lucide-text-quote"
          @mousedown.prevent
          @click="handleQuote"
        >
          Reply
        </Button>
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { isTextSelection, type Editor } from '@tiptap/core'
import { DOMSerializer } from '@tiptap/pm/model'
import { Button } from 'frappe-ui'
import LucideTextQuote from '~icons/lucide/text-quote'
import { buildDocTextIndex, extractQuotedText, occurrenceAt } from './quoteTextSearch'
import { useRichQuotes } from './useRichQuotes'

// sourceId/author identify the passage being quoted; the controller inserts the
// quote into the discussion's reply editor.
const props = defineProps<{ editor: Editor; sourceId: string; author: string }>()

const richQuotes = useRichQuotes()

const visible = ref(false)
const position = ref({ x: 0, y: 0 })

// On touch screens the OS draws its own Copy/Share toolbar above the selection,
// so the button goes below it instead, clear of the selection handles
const isCoarsePointer = useMediaQuery('(pointer: coarse)')

// Show the button only once a mouse or pen is released, so it doesn't flicker
// alongside the selection while dragging. Touch and keyboard selections show
// after a short settle delay instead.
let isPointerDown = false
let hiddenByScroll = false
let settleTimer: ReturnType<typeof setTimeout> | undefined
let editorDom: HTMLElement | null = null

function hasQuotableSelection() {
  const { state } = props.editor
  const { selection } = state
  if (props.editor.isEditable || selection.empty) return false
  // a NodeSelection (clicking an image/video) is also non-empty — only offer
  // Reply for ranged text selections with actual text in them
  if (!isTextSelection(selection)) return false
  return Boolean(state.doc.textBetween(selection.from, selection.to, ' ', ' ').trim())
}

// PM's selection state can lag behind the DOM (clicking outside the editor
// collapses the native selection without dispatching a transaction), so also
// check the live DOM selection before showing
function hasUsableDomSelection() {
  const sel = window.getSelection()
  return !!sel && !sel.isCollapsed && sel.rangeCount > 0 && !!editorDom?.contains(sel.anchorNode)
}

function evaluate() {
  hiddenByScroll = false
  if (isPointerDown || !hasQuotableSelection() || !hasUsableDomSelection()) {
    visible.value = false
    return
  }
  const rect = window.getSelection()!.getRangeAt(0).getBoundingClientRect()
  if (!rect || (rect.width === 0 && rect.height === 0)) {
    visible.value = false
    return
  }
  // The page scrolled the selection out of view. The clamps below would pin the
  // button to a screen edge, away from the text it quotes, so wait until a scroll
  // brings the text back
  if (rect.bottom < 0 || rect.top > window.innerHeight) {
    visible.value = false
    hiddenByScroll = true
    return
  }
  const margin = 60
  const x = Math.min(Math.max(rect.left + rect.width / 2, margin), window.innerWidth - margin)
  const y = isCoarsePointer.value
    ? Math.min(rect.bottom, window.innerHeight - margin)
    : Math.max(rect.top, margin)
  position.value = { x, y }
  visible.value = true
}

function scheduleEvaluate() {
  clearTimeout(settleTimer)
  settleTimer = setTimeout(evaluate, 400)
}

// Every comment has its own button, so ignore selection changes that neither
// start inside this editor nor need this button hidden
function onSelectionChange() {
  if (visible.value || editorDom?.contains(window.getSelection()?.anchorNode ?? null)) {
    scheduleEvaluate()
  }
}

function onPointerDown(event: PointerEvent) {
  visible.value = false
  // a touch long-press hands the gesture to the browser's text selection, which
  // fires pointercancel and never pointerup, so leave touch to the settle delay
  if (event.pointerType === 'touch') return
  isPointerDown = true
}

function onPointerUp() {
  if (!isPointerDown) return
  isPointerDown = false
  evaluate()
}

// Hide while scrolling, then check again once scrolling stops: the selection
// often survives, and on touch, dragging a selection handle can nudge the page
function onScroll() {
  if (!visible.value && !hiddenByScroll) return
  visible.value = false
  hiddenByScroll = true
  scheduleEvaluate()
}

function attachListeners() {
  editorDom = props.editor.view.dom
  editorDom.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
  window.addEventListener('scroll', onScroll, true)
  // The DOM event, not the editor's selectionUpdate: a read-only editor misses the
  // selection collapsing (a tap elsewhere), so reselecting the same words would
  // look unchanged to it and the button would never come back
  document.addEventListener('selectionchange', onSelectionChange)
}

onMounted(() => {
  // editor.view is a throwing proxy until EditorContent mounts the view, and
  // this component (in the #top slot) mounts before it — attach on 'mount'
  if (props.editor.isInitialized) {
    attachListeners()
  } else {
    props.editor.once('mount', attachListeners)
  }
})

onBeforeUnmount(() => {
  clearTimeout(settleTimer)
  props.editor.off('mount', attachListeners)
  document.removeEventListener('selectionchange', onSelectionChange)
  editorDom?.removeEventListener('pointerdown', onPointerDown)
  editorDom = null
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  window.removeEventListener('scroll', onScroll, true)
})

function handleQuote() {
  const { state } = props.editor
  const { from, to } = state.selection
  const slice = state.doc.slice(from, to)
  const serializer = DOMSerializer.fromSchema(state.schema)
  const div = document.createElement('div')
  div.appendChild(serializer.serializeFragment(slice.content))
  // record which occurrence of this text in the source was selected, so it can
  // be re-located unambiguously even when the same passage appears more than once
  const occurrence = occurrenceAt(buildDocTextIndex(state.doc), extractQuotedText(div), from)
  richQuotes?.requestQuote({
    sourceId: props.sourceId,
    author: props.author,
    html: div.innerHTML,
    occurrence,
  })
  visible.value = false
}
</script>
