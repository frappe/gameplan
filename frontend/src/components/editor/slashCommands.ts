import { SlashCommands } from 'frappe-ui/editor'
import type { AnyExtension, Editor, Range } from '@tiptap/core'
import { collapsibleSlashItem } from './collapsible'
import { footnoteSlashItem } from './footnotes'

type SlashItemsProps = { query: string; editor: Editor }
type SlashCommandsOptions = {
  suggestion?: {
    items?: (props: SlashItemsProps) => SlashItem[] | Promise<SlashItem[]>
    [key: string]: unknown
  }
  [key: string]: unknown
}
export type SlashItem = {
  title: string
  icon: string
  group?: string
  isAvailable?: (editor: Editor) => boolean
  command: (props: { editor: Editor; range: Range }) => void
}

const gameplanSlashItems: SlashItem[] = [collapsibleSlashItem, footnoteSlashItem]

/**
 * frappe-ui's slash-command registry is a closed list built inside the
 * extension, so gameplan-only commands are added by wrapping its `items`
 * resolver rather than editing the library. Kept local because these nodes are
 * gameplan-only; if one moves into frappe-ui, its command moves with it.
 */
export function gameplanSlashCommands(): AnyExtension {
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
            const query = props.query.toLowerCase()
            const extra = gameplanSlashItems.filter(
              (item) =>
                (item.isAvailable?.(props.editor) ?? true) &&
                (!query || item.title.toLowerCase().includes(query)),
            )
            return [...base, ...extra]
          },
        },
      }
    },
  }) as AnyExtension
}
