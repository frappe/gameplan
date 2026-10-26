import type { CommandProps, JSONContent } from '@tiptap/core'

export function insertCard(card: JSONContent) {
  return ({ tr, commands }: CommandProps) => {
    const { $from } = tr.selection
    const paragraph = { type: 'paragraph' }
    if ($from.parent.isTextblock && $from.parent.content.size === 0 && $from.depth > 0) {
      const range = { from: $from.before(), to: $from.after() }
      const isLast = range.to === tr.doc.content.size
      return commands.insertContentAt(range, isLast ? [card, paragraph] : card)
    }
    const isLast = $from.depth > 0 && $from.after() === tr.doc.content.size
    const atEnd = $from.parentOffset === $from.parent.content.size
    return commands.insertContent(isLast && atEnd ? [card, paragraph] : card)
  }
}
