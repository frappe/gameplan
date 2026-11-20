import type { MenuItem } from 'frappe-ui/editor'
import type { Editor } from '@tiptap/core'
import type { SlashItem } from '../slashCommands'

const LABEL = 'Collapsible section'
const ICON = 'lucide-chevron-right'

const hasCollapsible = (editor: Editor) => 'collapsible' in editor.schema.nodes

/** Toolbar / floating-menu entry. Hides itself when the node isn't loaded. */
export const CollapsibleSection: MenuItem = {
  label: LABEL,
  icon: ICON,
  action: (editor) => {
    editor.chain().focus().setCollapsible().run()
  },
  isActive: (editor) => editor.isActive('collapsible'),
  isAvailable: hasCollapsible,
}

export const collapsibleSlashItem: SlashItem = {
  title: LABEL,
  icon: ICON,
  // Matches the last group in frappe-ui's built-in registry, so the item lands
  // under the existing "Insert" header instead of starting a stray second one.
  group: 'Insert',
  isAvailable: hasCollapsible,
  command: ({ editor, range }) => {
    editor.chain().focus().deleteRange(range).setCollapsible().run()
  },
}
