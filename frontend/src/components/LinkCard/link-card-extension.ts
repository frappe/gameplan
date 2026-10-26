import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import { insertCard } from '@/components/editor/insertCard'
import LinkCardView from './LinkCardView.vue'

export interface LinkCardAttrs {
  href: string
  title: string
  description?: string
  image?: string
  siteName?: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    linkCard: {
      insertLinkCard: (attrs: LinkCardAttrs) => ReturnType
    }
  }
}

function dataAttribute(name: string) {
  return {
    default: '',
    parseHTML: (element: HTMLElement) => element.getAttribute(`data-${name}`) ?? '',
    renderHTML: (attributes: Record<string, string>) => {
      const key = name.replace(/-(\w)/g, (_, c) => c.toUpperCase())
      return attributes[key] ? { [`data-${name}`]: attributes[key] } : {}
    },
  }
}

export const LinkCardExtension = Node.create({
  name: 'linkCard',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
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
      description: dataAttribute('description'),
      image: dataAttribute('image'),
      siteName: dataAttribute('site-name'),
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="link-card"]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'div',
      mergeAttributes({ 'data-type': 'link-card' }, HTMLAttributes),
      ['a', { href: node.attrs.href }, node.attrs.title || node.attrs.href],
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(LinkCardView)
  },

  addCommands() {
    return {
      insertLinkCard: (attrs) => insertCard({ type: this.name, attrs }),
    }
  },
})

export default LinkCardExtension
