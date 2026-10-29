import type { MenuItem } from 'frappe-ui/editor'
import type { Editor } from '@tiptap/core'
import type { SlashItem } from '../slashCommands'

const LABEL = 'Footnote'
const ICON = 'lucide-superscript'

const hasFootnotes = (editor: Editor) => 'footnoteReference' in editor.schema.nodes

/** Toolbar entry. Hides itself when the nodes aren't loaded. */
export const InsertFootnote: MenuItem = {
  label: LABEL,
  icon: ICON,
  action: (editor) => {
    editor.chain().focus().insertFootnote().run()
  },
  isDisabled: (editor) => !editor.can().insertFootnote(),
  isAvailable: hasFootnotes,
}

export const footnoteSlashItem: SlashItem = {
  title: LABEL,
  icon: ICON,
  group: 'Insert',
  isAvailable: hasFootnotes,
  command: ({ editor, range }) => {
    // "/" only opens the menu after a space, but a marker sits against its
    // word, so the space typed before "/" goes too.
    const before = editor.state.doc.textBetween(Math.max(0, range.from - 1), range.from)
    const from = before === ' ' ? range.from - 1 : range.from
    editor.chain().focus().deleteRange({ from, to: range.to }).insertFootnote().run()
  },
}
