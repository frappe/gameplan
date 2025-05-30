import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import RichQuoteNodeView from './RichQuoteNodeView.vue'

export interface RichQuoteOptions {
  HTMLAttributes: Record<string, any>
  onClick?: (props: { quoteId: string; author: string; content: string }) => void
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    richQuote: {
      /**
       * Set a rich quote with a specific quoteId
       */
      setRichQuote: (attributes: { quoteId: string }) => ReturnType
      /**
       * Toggle a rich quote with a specific quoteId
       */
      toggleRichQuote: (attributes: { quoteId: string }) => ReturnType
      /**
       * Unset a rich quote
       */
      unsetRichQuote: () => ReturnType
    }
  }
}

export const RichQuoteNodeExtension = Node.create<RichQuoteOptions>({
  name: 'richQuote',
  content: 'block+',
  group: 'block',
  atom: true,

  addOptions() {
    return {
      HTMLAttributes: {},
      onClick: () => {
        console.log('RichQuote clicked, but no onClick handler provided.')
      },
    }
  },

  addAttributes() {
    return {
      quoteId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-rich-quote-id'),
        renderHTML: (attributes) => {
          if (!attributes.quoteId) {
            return {}
          }
          return {
            'data-rich-quote-id': attributes.quoteId,
          }
        },
      },
      author: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-author'),
        renderHTML: (attributes) => {
          if (!attributes.author) {
            return {}
          }
          return {
            'data-author': attributes.author,
          }
        },
      },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'blockquote[data-rich-quote-id]',
        priority: 51, // Default blockquote priority is 50
      },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return ['blockquote', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes), 0]
  },

  addNodeView() {
    return VueNodeViewRenderer(RichQuoteNodeView)
  },

  addCommands() {
    return {
      setRichQuote:
        (attributes) =>
        ({ commands }) => {
          if (!attributes.quoteId) {
            console.warn('quoteId is required to set a richQuote.')
            return false
          }
          return commands.wrapIn(this.name, attributes)
        },
      toggleRichQuote:
        (attributes) =>
        ({ commands }) => {
          if (!attributes.quoteId) {
            console.warn('quoteId is required to toggle a richQuote.')
            return false
          }
          return commands.toggleWrap(this.name, attributes)
        },
      unsetRichQuote:
        () =>
        ({ commands }) => {
          return commands.lift(this.name)
        },
    }
  },
})

export default RichQuoteNodeExtension
