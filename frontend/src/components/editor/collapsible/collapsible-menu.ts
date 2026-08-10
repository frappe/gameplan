import { SlashCommands, type MenuItem } from 'frappe-ui/editor'
import type { AnyExtension, Editor, Range } from '@tiptap/core'

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

type SlashItemsProps = { query: string; editor: Editor }
type SlashCommandsOptions = {
  suggestion?: {
    items?: (props: SlashItemsProps) => SlashItem[] | Promise<SlashItem[]>
    [key: string]: unknown
  }
  [key: string]: unknown
}
type SlashItem = {
  title: string
  icon: string
  group?: string
  isAvailable?: (editor: Editor) => boolean
  command: (props: { editor: Editor; range: Range }) => void
}

const collapsibleSlashItem: SlashItem = {
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

/**
 * frappe-ui's slash-command registry is a closed list built inside the
 * extension, so a gameplan-only command is added by wrapping its `items`
 * resolver rather than editing the library. Kept local because this node is
 * gameplan-only; if the node ever moves into frappe-ui, the command moves with
 * it and this wrapper goes away.
 */
export function slashCommandsWithCollapsible(): AnyExtension {
  return SlashCommands.extend({
    // `this.parent()` is the library's own addOptions, so the built-in registry
    // is read through tiptap's inheritance rather than off a frozen `.options`.
    addOptions() {
      const parent = this.parent?.() as SlashCommandsOptions
      const baseItems = parent?.suggestion?.items
      return {
        ...parent,
        suggestion: {
          ...parent?.suggestion,
          items: async (props: SlashItemsProps) => {
            const base = baseItems ? await baseItems(props) : []
            if (!hasCollapsible(props.editor)) return base
            const query = props.query.toLowerCase()
            if (query && !LABEL.toLowerCase().includes(query)) return base
            return [...base, collapsibleSlashItem]
          },
        },
      }
    },
  }) as AnyExtension
}
