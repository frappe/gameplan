import { Node, mergeAttributes, type Editor } from '@tiptap/core'
import type { Node as PMNode, Schema } from '@tiptap/pm/model'
import {
  Plugin,
  PluginKey,
  TextSelection,
  type EditorState,
  type Transaction,
} from '@tiptap/pm/state'
import { Decoration, DecorationSet, type EditorView } from '@tiptap/pm/view'

/**
 * Footnotes: a numbered marker in the text and a matching note in one list at
 * the end of the document.
 *
 * Stored as `<sup data-type="footnote-reference" data-id="…">1</sup>` in the
 * text and `<ol data-type="footnotes"><li data-type="footnote" data-id="…">…</li></ol>`
 * after the last block. The number is written into the marker and the list is a real
 * `<ol>`, so the stored HTML still reads correctly where it is shown without
 * the editor — email digests, search previews. Links between the two are made
 * by the editor from `data-id`, not by `href`/`id`, because one page can show
 * many posts and each post numbers its notes from 1.
 * `gameplan/tests/platform/test_footnote_html.py` pins that this shape survives
 * sanitization.
 *
 * The author only places markers. One plugin keeps the list in step with them:
 * the list follows marker order, a new marker gets an empty note, a removed
 * marker takes its note with it, and a removed note takes its marker with it.
 */

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    footnote: {
      /** Insert a footnote marker after the selection and put the caret in its note. */
      insertFootnote: () => ReturnType
    }
  }
}

const REFERENCE = 'footnoteReference'
const LIST = 'footnotes'
const NOTE = 'footnote'

// Reuses the rich-quote flash (index.css) so every "jump here" looks the same.
const FLASH_CLASS = 'highlighted-quote-target'
const FLASH_MS = 2500

export const FootnoteReference = Node.create({
  name: REFERENCE,
  group: 'inline',
  inline: true,
  atom: true,
  selectable: false,

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-id'),
        renderHTML: (attributes) => ({ 'data-id': attributes.id }),
      },
      // Derived from marker order by the plugin. Written as the marker's text,
      // not as an attribute.
      number: {
        default: 1,
        parseHTML: (element) => Number(element.textContent) || 1,
        rendered: false,
      },
    }
  },

  parseHTML() {
    return [{ tag: 'sup[data-type="footnote-reference"]', priority: 60 }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'sup',
      mergeAttributes(HTMLAttributes, { 'data-type': 'footnote-reference' }),
      String(node.attrs.number),
    ]
  },

  renderText({ node }) {
    return `[${node.attrs.number}]`
  },

  addCommands() {
    return {
      insertFootnote:
        () =>
        ({ state, tr, dispatch }) => {
          const type = state.schema.nodes[REFERENCE]
          const at = state.selection.to
          // A note cannot carry its own footnote: the list holds markers' notes only.
          if (noteAround(state)) return false
          if (!state.doc.resolve(at).parent.type.contentMatch.matchType(type)) return false
          if (!dispatch) return true

          const id = newId()
          tr.insert(at, type.create({ id }))
          syncFootnotes(tr, new Map())
          const note = findNote(tr.doc, id)
          if (note) {
            tr.setSelection(
              TextSelection.near(tr.doc.resolve(note.pos + note.node.nodeSize - 2), -1),
            )
          }
          tr.scrollIntoView()
          return true
        },
    }
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Alt-f': () => this.editor.commands.insertFootnote(),
    }
  },

  addProseMirrorPlugins() {
    // Notes whose marker was cut, by id, so pasting the marker back brings its
    // text with it. Lives as long as the editor.
    const removedNotes = new Map<string, PMNode>()
    const editor = this.editor

    return [
      new Plugin({
        key: new PluginKey('footnoteSync'),
        appendTransaction(transactions, oldState, newState) {
          if (!transactions.some((tr) => tr.docChanged)) return null
          const tr = newState.tr
          removeMarkersOfDeletedNotes(tr, oldState)
          syncFootnotes(tr, removedNotes)
          return tr.docChanged ? tr : null
        },
        props: {
          decorations: (state) => footnoteDecorations(state, editor),
          handleClickOn(view, _pos, node, nodePos, event) {
            if (node.type.name !== REFERENCE) return false
            event.preventDefault()
            jumpToNote(view, node.attrs.id, editor.isEditable)
            return true
          },
        },
      }),
    ]
  },
})

export const Footnotes = Node.create({
  name: LIST,
  group: 'block',
  content: `${NOTE}+`,
  isolating: true,
  selectable: false,
  draggable: false,

  parseHTML() {
    // Above OrderedList's plain `ol` rule, which would otherwise claim it.
    return [{ tag: 'ol[data-type="footnotes"]', priority: 60 }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['ol', mergeAttributes(HTMLAttributes, { 'data-type': 'footnotes' }), 0]
  },
})

export const Footnote = Node.create({
  name: NOTE,
  content: 'paragraph+',
  defining: true,
  isolating: true,
  selectable: false,

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-id'),
        renderHTML: (attributes) => ({ 'data-id': attributes.id }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'li[data-type="footnote"]', priority: 60 }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['li', mergeAttributes(HTMLAttributes, { 'data-type': 'footnote' }), 0]
  },

  addKeyboardShortcuts() {
    return {
      // Backspace at the start of a note would join it into the note above.
      // In an empty note it removes the footnote instead; with text it stops.
      Backspace: ({ editor }) => {
        const { selection } = editor.state
        if (!selection.empty) return false
        const note = noteAround(editor.state)
        if (!note || selection.from !== note.pos + 2) return false
        if (note.node.textContent.trim()) return true
        return removeFootnote(editor, note.node.attrs.id)
      },
    }
  },
})

/** All three nodes load together: the list needs notes and notes need markers. */
export const footnoteExtensions = () => [FootnoteReference, Footnotes, Footnote]

/**
 * Rebuilds the notes list from the markers in `tr.doc`: one note per marker, in
 * marker order, as the last block. Notes without a marker are kept in
 * `removedNotes` in case the marker comes back. Changes nothing when the
 * document is already in step, so it is safe to run after every transaction.
 */
function syncFootnotes(tr: Transaction, removedNotes: Map<string, PMNode>) {
  const schema = tr.doc.type.schema
  const markers: { pos: number; node: PMNode }[] = []
  const lists: { pos: number; node: PMNode }[] = []
  const notes = new Map<string, PMNode>()

  tr.doc.descendants((node, pos) => {
    if (node.type.name === REFERENCE) markers.push({ pos, node })
    if (node.type.name === LIST) {
      lists.push({ pos, node })
      node.forEach((note) => {
        if (!notes.has(note.attrs.id)) notes.set(note.attrs.id, note)
      })
      return false
    }
  })

  // Attribute-only steps first: they do not move any position.
  const seen = new Set<string>()
  const ids = markers.map(({ pos, node }, index) => {
    // A pasted copy of a marker carries the original's id; give it its own note.
    const id = node.attrs.id && !seen.has(node.attrs.id) ? node.attrs.id : newId()
    seen.add(id)
    const number = index + 1
    if (id !== node.attrs.id || number !== node.attrs.number) {
      tr.setNodeMarkup(pos, undefined, { ...node.attrs, id, number })
    }
    return id
  })

  for (const [id, note] of notes) {
    if (!seen.has(id)) removedNotes.set(id, note)
  }

  const list = ids.length
    ? schema.nodes[LIST].create(
        null,
        ids.map((id) => notes.get(id) ?? removedNotes.get(id) ?? emptyNote(schema, id)),
      )
    : null

  if (!list && !lists.length) return
  if (list && lists.length === 1 && lists[0].node.eq(list)) return

  // The list stays where it is (the last one wins when a paste brought in a
  // second). It is not forced to be the last block: that would fight
  // TrailingNode, which appends a paragraph after it unless told not to.
  const last = lists.at(-1)
  if (list && last) {
    tr.replaceWith(last.pos, last.pos + last.node.nodeSize, list)
  } else if (list) {
    tr.insert(tr.doc.content.size, list)
  }
  for (const { pos, node } of lists.slice(0, list ? -1 : undefined).reverse()) {
    tr.delete(tr.mapping.map(pos), tr.mapping.map(pos + node.nodeSize))
  }
}

/** A note deleted by hand (its whole list item) takes its marker with it. */
function removeMarkersOfDeletedNotes(tr: Transaction, oldState: EditorState) {
  const before = noteIds(oldState.doc)
  const after = noteIds(tr.doc)
  const deleted = [...before].filter((id) => !after.has(id))
  if (!deleted.length) return

  const doomed: { pos: number; size: number }[] = []
  tr.doc.descendants((node, pos) => {
    if (node.type.name === REFERENCE && deleted.includes(node.attrs.id)) {
      doomed.push({ pos, size: node.nodeSize })
    }
  })
  for (const { pos, size } of doomed.reverse()) tr.delete(pos, pos + size)
}

function removeFootnote(editor: Editor, id: string) {
  const marker = findMarker(editor.state.doc, id)
  if (!marker) return false
  return editor
    .chain()
    .command(({ tr }) => {
      tr.delete(marker.pos, marker.pos + marker.node.nodeSize)
      tr.setSelection(TextSelection.near(tr.doc.resolve(marker.pos)))
      return true
    })
    .run()
}

/**
 * Adds a "back to text" link to the end of each note, and a hover preview of
 * the note text to each marker.
 */
function footnoteDecorations(state: EditorState, editor: Editor) {
  const decorations: Decoration[] = []
  const noteText = new Map<string, string>()
  state.doc.descendants((node, pos) => {
    if (node.type.name !== NOTE) return
    noteText.set(node.attrs.id, node.textContent.trim())
    const end = pos + node.nodeSize - 2
    decorations.push(
      Decoration.widget(end, (view) => backLink(view, node.attrs.id, editor), {
        side: 1,
        key: `footnote-back-${node.attrs.id}`,
        ignoreSelection: true,
      }),
    )
    return false
  })
  state.doc.descendants((node, pos) => {
    if (node.type.name !== REFERENCE) return
    const text = noteText.get(node.attrs.id)
    decorations.push(
      Decoration.node(pos, pos + node.nodeSize, {
        title: text ? truncate(text, 200) : 'Empty footnote',
        role: 'link',
        'aria-label': `Footnote ${node.attrs.number}`,
      }),
    )
  })
  return DecorationSet.create(state.doc, decorations)
}

function backLink(view: EditorView, id: string, editor: Editor) {
  const button = document.createElement('button')
  button.type = 'button'
  button.className = 'footnote-back-link'
  button.contentEditable = 'false'
  button.textContent = '↩'
  button.title = 'Back to text'
  button.setAttribute('aria-label', 'Back to text')
  button.addEventListener('mousedown', (event) => event.preventDefault())
  button.addEventListener('click', (event) => {
    event.preventDefault()
    jumpToMarker(view, id, editor.isEditable)
  })
  return button
}

function jumpToNote(view: EditorView, id: string, editable: boolean) {
  const note = findNote(view.state.doc, id)
  if (!note) return
  if (editable) {
    const end = note.pos + note.node.nodeSize - 2
    view.dispatch(view.state.tr.setSelection(TextSelection.near(view.state.doc.resolve(end), -1)))
    view.focus()
  }
  flash(view.nodeDOM(note.pos))
}

function jumpToMarker(view: EditorView, id: string, editable: boolean) {
  const marker = findMarker(view.state.doc, id)
  if (!marker) return
  if (editable) {
    const after = marker.pos + marker.node.nodeSize
    view.dispatch(view.state.tr.setSelection(TextSelection.create(view.state.doc, after)))
    view.focus()
  }
  flash(view.nodeDOM(marker.pos))
}

function flash(dom: globalThis.Node | null) {
  if (!(dom instanceof HTMLElement)) return
  dom.scrollIntoView({ behavior: 'smooth', block: 'center' })
  dom.classList.remove(FLASH_CLASS)
  // Restart the animation when the same target is flashed twice in a row.
  void dom.offsetWidth
  dom.classList.add(FLASH_CLASS)
  setTimeout(() => dom.classList.remove(FLASH_CLASS), FLASH_MS)
}

function noteAround(state: EditorState) {
  const { $from } = state.selection
  for (let depth = $from.depth; depth > 0; depth--) {
    const node = $from.node(depth)
    if (node.type.name === NOTE) return { node, pos: $from.before(depth) }
  }
  return null
}

function findNote(doc: PMNode, id: string) {
  return findNode(doc, NOTE, id)
}

function findMarker(doc: PMNode, id: string) {
  return findNode(doc, REFERENCE, id)
}

function findNode(doc: PMNode, type: string, id: string) {
  let found: { node: PMNode; pos: number } | null = null
  doc.descendants((node, pos) => {
    if (found) return false
    if (node.type.name === type && node.attrs.id === id) found = { node, pos }
  })
  return found as { node: PMNode; pos: number } | null
}

function noteIds(doc: PMNode) {
  const ids = new Set<string>()
  doc.descendants((node) => {
    if (node.type.name === NOTE) ids.add(node.attrs.id)
  })
  return ids
}

function emptyNote(schema: Schema, id: string) {
  return schema.nodes[NOTE].create({ id }, schema.nodes.paragraph.create())
}

function newId() {
  return Math.random().toString(36).slice(2, 10)
}

function truncate(text: string, length: number) {
  return text.length > length ? `${text.slice(0, length - 1)}…` : text
}
