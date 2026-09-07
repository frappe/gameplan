import { InputRule, Node, mergeAttributes } from '@tiptap/core'
import { TextSelection } from '@tiptap/pm/state'
import { Fragment } from '@tiptap/pm/model'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import CollapsibleNodeView from './CollapsibleNodeView.vue'

/**
 * A collapsible ("toggle") section: a click-to-expand title with arbitrary block
 * content underneath.
 *
 * Serialized as semantic `<details open><summary>…</summary><div
 * data-type="collapsible-content">…</div></details>` so it still collapses
 * natively wherever the stored HTML is rendered without the editor — email
 * digests, search previews. `details`, `summary` and the `open` attribute are all
 * in frappe's sanitizer allowlist, so this shape survives a save untouched;
 * `gameplan/tests/platform/test_collapsible_html.py` pins that, since a dropped
 * tag or attribute fails silently rather than raising.
 *
 * The three nodes are separate on purpose: `collapsible` owns the open/closed
 * attribute and the node view, `collapsibleSummary` is a one-line inline
 * container (so Enter can mean "go to the body" instead of "new paragraph"), and
 * `collapsibleContent` holds normal blocks — including nested collapsibles.
 */

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    collapsible: {
      /** Insert an empty collapsible section and put the caret in its title. */
      setCollapsible: () => ReturnType
      /** Unwrap the collapsible around the caret, keeping title and body as blocks. */
      unsetCollapsible: () => ReturnType
      /** Expand or collapse the section around the caret. */
      toggleCollapsibleOpen: () => ReturnType
    }
  }
}

export const CollapsibleSummary = Node.create({
  name: 'collapsibleSummary',
  content: 'inline*',
  defining: true,
  selectable: false,

  parseHTML() {
    return [{ tag: 'summary' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['summary', mergeAttributes(HTMLAttributes), 0]
  },
})

export const CollapsibleContent = Node.create({
  name: 'collapsibleContent',
  content: 'block+',
  defining: true,
  selectable: false,

  parseHTML() {
    return [{ tag: 'div[data-type="collapsible-content"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'collapsible-content' }), 0]
  },
})

export const Collapsible = Node.create({
  name: 'collapsible',
  group: 'block',
  content: 'collapsibleSummary collapsibleContent',
  defining: true,
  // Keeps a select-all / drag from merging a collapsible into a neighbouring
  // block and leaving a half-built section behind.
  isolating: true,

  addAttributes() {
    return {
      open: {
        default: true,
        parseHTML: (element) => element.hasAttribute('open'),
        // The HTML boolean attribute: present means open, absent means closed.
        renderHTML: (attributes) => (attributes.open ? { open: '' } : {}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'details' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['details', mergeAttributes(HTMLAttributes), 0]
  },

  addNodeView() {
    return VueNodeViewRenderer(CollapsibleNodeView)
  },

  addCommands() {
    return {
      setCollapsible:
        () =>
        ({ chain, state }) => {
          const from = state.selection.from
          return chain()
            .insertContent({
              type: this.name,
              attrs: { open: true },
              content: [
                { type: CollapsibleSummary.name },
                {
                  type: CollapsibleContent.name,
                  content: [{ type: 'paragraph' }],
                },
              ],
            })
            .command(({ tr, dispatch }) => {
              if (!dispatch) return true
              // `insertContent` gives no handle on what it inserted, so find the
              // first summary at or after the original caret and land in it.
              let target: number | null = null
              tr.doc.nodesBetween(Math.max(0, from - 1), tr.doc.content.size, (node, pos) => {
                if (target === null && node.type.name === CollapsibleSummary.name) {
                  target = pos + 1
                }
              })
              if (target !== null) {
                tr.setSelection(TextSelection.create(tr.doc, target))
              }
              return true
            })
            .run()
        },

      unsetCollapsible:
        () =>
        ({ state, tr, dispatch }) => {
          const found = findCollapsible(state)
          if (!found) return false
          if (dispatch) {
            const summary = found.node.child(0)
            const content = found.node.child(1)
            // The title becomes a plain paragraph above the body it used to hide.
            const paragraph = state.schema.nodes.paragraph.create(null, summary.content)
            tr.replaceWith(
              found.pos,
              found.pos + found.node.nodeSize,
              Fragment.from(paragraph).append(content.content),
            )
          }
          return true
        },

      toggleCollapsibleOpen:
        () =>
        ({ state, tr, dispatch }) => {
          const found = findCollapsible(state)
          if (!found) return false
          if (dispatch) {
            tr.setNodeAttribute(found.pos, 'open', !found.node.attrs.open)
          }
          return true
        },
    }
  },

  addInputRules() {
    return [
      new InputRule({
        // Notion's `>` is already blockquote in the starter kit, so the toggle
        // takes `>>`. Anything typed after it on the line becomes the title.
        //
        // `»` is not an alternative spelling — it is what the user's `>>` has
        // already become. The Typography extension (loaded by RichTextKit, not
        // by CommentKit) rewrites `>>` to a guillemet on the second keystroke,
        // before the space that triggers this rule. Matching both is what makes
        // the same trigger work in a discussion body and in a comment.
        find: /^(?:>>|»)\s$/,
        handler: ({ state, range }) => {
          const $start = state.doc.resolve(range.from)
          const paragraph = $start.parent
          if (paragraph.type.name !== 'paragraph') return null

          const paragraphStart = $start.start()
          const rest = paragraph.content.cut(range.to - paragraphStart)
          const { schema } = state
          // `state` here is tiptap's chainable state, so `state.tr` is the one
          // transaction the input-rule plugin applies — not a fresh one.
          const tr = state.tr
          const node = schema.nodes[this.name].create({ open: true }, [
            schema.nodes[CollapsibleSummary.name].create(null, rest),
            schema.nodes[CollapsibleContent.name].create(null, schema.nodes.paragraph.create()),
          ])

          tr.replaceWith(paragraphStart - 1, $start.end() + 1, node)
          // Caret at the end of the text that moved into the title.
          tr.setSelection(TextSelection.create(tr.doc, paragraphStart + 1 + rest.size))
        },
      }),
    ]
  },

  addKeyboardShortcuts() {
    return {
      // Enter in the title moves into the body rather than splitting the title,
      // which the schema (`collapsibleSummary` is a single node) forbids anyway.
      Enter: ({ editor }) => {
        const { state } = editor
        if (!state.selection.empty) return false
        const found = findCollapsible(state)
        if (!found || !isInSummary(state)) return false

        const contentStart = found.pos + 1 + found.node.child(0).nodeSize + 1
        return editor
          .chain()
          .command(({ tr, dispatch }) => {
            // Entering a collapsed section would type into hidden content.
            if (!found.node.attrs.open && dispatch) {
              tr.setNodeAttribute(found.pos, 'open', true)
            }
            return true
          })
          .setTextSelection(contentStart + 1)
          .run()
      },

      // Backspace at the very start of an empty title unwraps the section, the
      // same escape hatch a blockquote or list item gives.
      Backspace: ({ editor }) => {
        const { state } = editor
        if (!state.selection.empty || !isInSummary(state)) return false
        const found = findCollapsible(state)
        if (!found) return false
        if (state.selection.from !== found.pos + 2) return false
        return editor.commands.unsetCollapsible()
      },
    }
  },
})

function findCollapsible(state: { selection: { $from: any } }) {
  const { $from } = state.selection
  for (let depth = $from.depth; depth > 0; depth--) {
    const node = $from.node(depth)
    if (node.type.name === Collapsible.name) {
      return { node, pos: $from.before(depth) }
    }
  }
  return null
}

function isInSummary(state: { selection: { $from: any } }) {
  const { $from } = state.selection
  for (let depth = $from.depth; depth > 0; depth--) {
    if ($from.node(depth).type.name === CollapsibleSummary.name) return true
  }
  return false
}

/** The three nodes always load together — the parent's schema requires both children. */
export const collapsibleExtensions = () => [Collapsible, CollapsibleSummary, CollapsibleContent]
