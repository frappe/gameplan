import { mergeAttributes, type CommandProps, type JSONContent } from '@tiptap/core'
import type { DOMOutputSpec, Node as ProseMirrorNode } from '@tiptap/pm/model'

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

export function cardLinkAttributes() {
  return {
    href: {
      default: null,
      parseHTML: (element: HTMLElement) => element.querySelector('a')?.getAttribute('href') ?? null,
      renderHTML: () => ({}),
    },
    title: {
      default: '',
      parseHTML: (element: HTMLElement) => element.querySelector('a')?.textContent ?? '',
      renderHTML: () => ({}),
    },
  }
}

export function renderCard(type: string) {
  return ({
    node,
    HTMLAttributes,
  }: {
    node: ProseMirrorNode
    HTMLAttributes: Record<string, any>
  }): DOMOutputSpec => [
    'div',
    mergeAttributes({ 'data-type': type }, HTMLAttributes),
    ['a', { href: node.attrs.href }, node.attrs.title || node.attrs.href],
  ]
}
