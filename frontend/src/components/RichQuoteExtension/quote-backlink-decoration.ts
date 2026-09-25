import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import type { Node as PMNode } from '@tiptap/pm/model'
import { createApp, h, type App } from 'vue'
import { Button } from 'frappe-ui'
import { buildDocTextIndex, findDocRange } from './quoteTextSearch'
import type { QuoteBacklink } from './useRichQuotes'

export const quoteBacklinksPluginKey = new PluginKey<DecorationSet>('quoteBacklinks')

export interface QuoteBacklinkDecorationOptions {
  getBacklinks: () => QuoteBacklink[]
  onBacklinkClick: (props: { anchorEl: HTMLElement; items: QuoteBacklink[] }) => void
}

/**
 * Renders a small "quoted by" badge (❝ + count) after each passage of this
 * document that has been quoted in a comment. Backlinks arrive through a
 * getter because extension options aren't reactive — the host component
 * dispatches `tr.setMeta(quoteBacklinksPluginKey, 'refresh')` whenever the
 * backlink list or the editable state changes.
 */
export const QuoteBacklinkDecoration = Extension.create<QuoteBacklinkDecorationOptions>({
  name: 'quoteBacklinkDecoration',

  addOptions() {
    return {
      getBacklinks: () => [],
      onBacklinkClick: () => {},
    }
  },

  addProseMirrorPlugins() {
    const ext = this

    const compute = (doc: PMNode): DecorationSet => {
      // badges are a read-mode affordance; they'd also interfere with editing
      if (ext.editor.isEditable) return DecorationSet.empty

      const backlinks = ext.options.getBacklinks()
      if (!backlinks.length) return DecorationSet.empty

      // group by passage *and* occurrence: two comments quoting different
      // occurrences of the same text get badges on their respective passages
      const groups = new Map<string, { quotedText: string; occurrence: number; items: QuoteBacklink[] }>()
      for (const backlink of backlinks) {
        const key = `${backlink.occurrence} ${backlink.quotedText}`
        let group = groups.get(key)
        if (!group) {
          group = { quotedText: backlink.quotedText, occurrence: backlink.occurrence, items: [] }
          groups.set(key, group)
        }
        group.items.push(backlink)
      }

      const index = buildDocTextIndex(doc)
      const decorations: Decoration[] = []
      for (const { quotedText, occurrence, items } of groups.values()) {
        const range = findDocRange(index, quotedText, occurrence)
        // passage may have been edited away since it was quoted — skip silently
        if (!range) continue

        // anchor at the passage start and float into the right lane (absolutely
        // positioned, so it never enters the text flow); side:-1 keeps it out of
        // the way of edits at the boundary
        const anchor = outsideTable(doc, range.from)
        decorations.push(
          Decoration.widget(anchor, () => createBadge(items, ext.options.onBacklinkClick), {
            side: -1,
            key: `quote-backlink:${anchor}:${items.length}:${quotedText.length}`,
            destroy: unmountBadge,
          }),
        )
      }
      return DecorationSet.create(doc, decorations)
    }

    return [
      new Plugin({
        key: quoteBacklinksPluginKey,
        state: {
          init: (_, state) => compute(state.doc),
          apply: (tr, old) => {
            if (tr.docChanged || tr.getMeta(quoteBacklinksPluginKey) === 'refresh') {
              return compute(tr.doc)
            }
            return old.map(tr.mapping, tr.doc)
          },
        },
        props: {
          decorations(state) {
            return this.getState(state)
          },
        },
      }),
    ]
  },
})

// Table cells are position: relative (frappe-ui editor styles), so a badge
// inside a cell would resolve `left-full` against the cell: it covers the next
// cell, or scrolls the table in the last column. Move the anchor to just before
// the table, so the badge resolves against the content column.
function outsideTable(doc: PMNode, pos: number): number {
  const $pos = doc.resolve(pos)
  for (let depth = 1; depth <= $pos.depth; depth++) {
    if ($pos.node(depth).type.spec.tableRole === 'table') return $pos.before(depth)
  }
  return pos
}

// The widget DOM hosts a mounted frappe-ui Button; remember its app so the
// widget's `destroy` hook can unmount it.
const badgeApps = new WeakMap<Node, App>()

function createBadge(
  items: QuoteBacklink[],
  onClick: QuoteBacklinkDecorationOptions['onBacklinkClick'],
): HTMLElement {
  const container = document.createElement('span')
  container.setAttribute('data-quote-backlink-widget', '')
  container.contentEditable = 'false'
  // Absolutely positioned at the passage start (see widget anchor) and pushed
  // past the content column into the right lane, so it floats alongside the
  // quoted text without disturbing the flow. Hidden on mobile (< sm), where the
  // content fills the width and there is no lane.
  container.className = 'absolute left-full ml-3 hidden sm:block'
  container.title = items.length > 1 ? `Quoted by ${items.length} comments` : 'Quoted by 1 comment'

  const multiple = items.length > 1
  const app = createApp(() =>
    h(Button, {
      variant: 'ghost',
      label: multiple ? String(items.length) : undefined,
      icon: multiple ? undefined : 'lucide-message-square-quote',
      iconLeft: multiple ? 'lucide-message-square-quote' : undefined,
      onClick: (event: MouseEvent) => {
        event.preventDefault()
        event.stopPropagation()
        onClick({ anchorEl: container, items })
      },
    }),
  )
  app.mount(container)
  badgeApps.set(container, app)
  return container
}

function unmountBadge(node: Node) {
  badgeApps.get(node)?.unmount()
  badgeApps.delete(node)
}

export default QuoteBacklinkDecoration
