import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import { insertCard } from '@/components/editor/insertCard'
import DiscussionCardView from './DiscussionCardView.vue'

export interface DiscussionCardAttrs {
  discussion: string
  href: string
  title: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    discussionCard: {
      insertDiscussionCard: (attrs: DiscussionCardAttrs) => ReturnType
    }
  }
}

export const DiscussionCardExtension = Node.create({
  name: 'discussionCard',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      discussion: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-discussion'),
        renderHTML: (attributes) =>
          attributes.discussion ? { 'data-discussion': attributes.discussion } : {},
      },
      href: {
        default: null,
        parseHTML: (element) => element.querySelector('a')?.getAttribute('href') ?? null,
        renderHTML: () => ({}),
      },
      title: {
        default: '',
        parseHTML: (element) => element.querySelector('a')?.textContent ?? '',
        renderHTML: () => ({}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="discussion-card"]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'div',
      mergeAttributes({ 'data-type': 'discussion-card' }, HTMLAttributes),
      ['a', { href: node.attrs.href }, node.attrs.title || node.attrs.href],
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(DiscussionCardView)
  },

  addCommands() {
    return {
      insertDiscussionCard: (attrs) => insertCard({ type: this.name, attrs }),
    }
  },
})

export default DiscussionCardExtension
