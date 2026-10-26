<template>
  <BubbleMenu
    :editor="editor"
    plugin-key="gpLinkToolbar"
    :should-show="shouldShow"
    :get-referenced-virtual-element="reference"
    :options="{ placement: 'bottom-start', offset: 4, flip: flipWithinEditor }"
  >
    <div
      class="flex items-center gap-1 rounded-4 border border-outline-gray-2 bg-surface-elevation-2 p-1 shadow-sm"
    >
      <Button
        v-if="target?.kind === 'card'"
        size="xs"
        variant="ghost"
        tooltip="Show as link"
        icon="lucide-link"
        @click="showAsLink"
      />
      <Button
        v-else
        size="xs"
        variant="ghost"
        tooltip="Show preview"
        icon="lucide-scan"
        :loading="loadingPreview"
        @click="showPreview"
      />
    </div>
  </BubbleMenu>
</template>

<script setup lang="ts">
import { ref, shallowRef } from 'vue'
import { getMarkRange, posToDOMRect, type Editor } from '@tiptap/core'
import { NodeSelection, type EditorState } from '@tiptap/pm/state'
import { BubbleMenu } from '@tiptap/vue-3/menus'
import { Button, toast } from 'frappe-ui'
import { fetchLinkPreview } from '@/data/linkPreviews'
import { extractServerMessage } from '@/utils'
import { parseDiscussionUrl } from '@/utils/discussionLinks'

type LinkTarget = {
  kind: 'link'
  from: number
  to: number
  href: string
  text: string
  discussion?: string
  external: boolean
}
type Target = LinkTarget | { kind: 'card'; pos: number }

const CARD_TYPES = ['discussionCard', 'linkCard']

const props = defineProps<{ editor: Editor }>()

const target = shallowRef<Target | null>(null)
const loadingPreview = ref(false)

function findTarget(state: EditorState): Target | null {
  const { selection, schema } = state
  if (selection instanceof NodeSelection && CARD_TYPES.includes(selection.node.type.name)) {
    return { kind: 'card', pos: selection.from }
  }
  if (!selection.empty) return null
  const linkType = schema.marks.link
  const { $from } = selection
  const inLink = (marks?: readonly { type: unknown }[]) => marks?.some((m) => m.type === linkType)
  const pos = inLink($from.nodeAfter?.marks)
    ? $from.pos
    : inLink($from.nodeBefore?.marks)
      ? $from.pos - 1
      : null
  if (pos === null) return null
  const range = getMarkRange(state.doc.resolve(pos), linkType)
  if (!range) return null
  const href = state.doc.nodeAt(pos)?.marks.find((m) => m.type === linkType)?.attrs.href ?? ''
  const discussion = parseDiscussionUrl(href)?.name
  const external = !discussion && /^https?:\/\//i.test(href)
  if (!discussion && !external) return null
  return {
    kind: 'link',
    ...range,
    href,
    text: state.doc.textBetween(range.from, range.to),
    discussion,
    external,
  }
}

function isSameLink(link: LinkTarget) {
  const { doc, schema } = props.editor.state
  if (link.to > doc.content.size || doc.textBetween(link.from, link.to) !== link.text) return false
  const mark = doc.nodeAt(link.from)?.marks.find((m) => m.type === schema.marks.link)
  return mark?.attrs.href === link.href
}

function shouldShow({ editor, state }: { editor: Editor; state: EditorState }) {
  target.value = editor.isEditable && editor.isFocused ? findTarget(state) : null
  return target.value !== null
}

function scrollParent(element: HTMLElement | null) {
  for (let el = element; el; el = el.parentElement) {
    if (/(auto|scroll)/.test(getComputedStyle(el).overflowY)) return el
  }
  return null
}

function flipWithinEditor() {
  return { boundary: scrollParent(props.editor.view.dom) ?? ('clippingAncestors' as const) }
}

function reference() {
  const current = target.value
  if (!current) return null
  const view = props.editor.view
  if (current.kind === 'card') {
    const dom = view.nodeDOM(current.pos) as HTMLElement | null
    return dom ? { getBoundingClientRect: () => dom.getBoundingClientRect() } : null
  }
  return { getBoundingClientRect: () => posToDOMRect(view, current.from, current.to) }
}

function showPreview() {
  const current = target.value
  if (current?.kind !== 'link') return
  if (current.discussion) {
    props.editor
      .chain()
      .focus()
      .deleteRange({ from: current.from, to: current.to })
      .insertDiscussionCard({
        discussion: current.discussion,
        href: current.href,
        title: current.text,
      })
      .run()
  } else if (current.external) {
    showLinkCard(current)
  }
}

async function showLinkCard(link: LinkTarget) {
  loadingPreview.value = true
  try {
    const preview = await fetchLinkPreview(link.href)
    if (props.editor.isDestroyed || !isSameLink(link)) return
    if (!preview) {
      toast.error('No preview available for this link')
      return
    }
    props.editor
      .chain()
      .focus()
      .deleteRange({ from: link.from, to: link.to })
      .insertLinkCard({
        href: link.href,
        title: preview.title,
        description: preview.description,
        image: preview.image,
        siteName: preview.site_name,
      })
      .run()
  } catch (error) {
    toast.error(extractServerMessage(error) || 'Could not load a preview for this link')
  } finally {
    loadingPreview.value = false
  }
}

function showAsLink() {
  const current = target.value
  if (current?.kind !== 'card') return
  const node = props.editor.state.doc.nodeAt(current.pos)
  if (!node) return
  const { href, title } = node.attrs
  props.editor
    .chain()
    .focus()
    .insertContentAt(
      { from: current.pos, to: current.pos + node.nodeSize },
      {
        type: 'paragraph',
        content: [
          { type: 'text', text: title || href, marks: [{ type: 'link', attrs: { href } }] },
        ],
      },
    )
    .run()
}
</script>
