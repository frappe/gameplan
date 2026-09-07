<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed z-20 -translate-x-1/2 -translate-y-full pb-1.5"
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

// Show the button only once the pointer is released, so it doesn't flicker
// alongside the selection while dragging. Keyboard selections show after a
// short settle delay instead.
let isPointerDown = false
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
  if (isPointerDown || !hasQuotableSelection() || !hasUsableDomSelection()) {
    visible.value = false
    return
  }
  const rect = window.getSelection()!.getRangeAt(0).getBoundingClientRect()
  if (!rect || (rect.width === 0 && rect.height === 0)) {
    visible.value = false
    return
  }
  const margin = 60
  const x = Math.min(Math.max(rect.left + rect.width / 2, margin), window.innerWidth - margin)
  position.value = { x, y: Math.max(rect.top, margin) }
  visible.value = true
}

function scheduleEvaluate() {
  clearTimeout(settleTimer)
  settleTimer = setTimeout(evaluate, 400)
}

function onPointerDown() {
  isPointerDown = true
  visible.value = false
}

function onPointerUp() {
  isPointerDown = false
  evaluate()
}

function onScroll() {
  if (visible.value) visible.value = false
}

function attachListeners() {
  editorDom = props.editor.view.dom
  editorDom.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('scroll', onScroll, true)
  props.editor.on('selectionUpdate', scheduleEvaluate)
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
  props.editor.off('selectionUpdate', scheduleEvaluate)
  editorDom?.removeEventListener('pointerdown', onPointerDown)
  editorDom = null
  window.removeEventListener('pointerup', onPointerUp)
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
