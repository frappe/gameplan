import { Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import { cardLinkAttributes, insertCard, renderCard } from '@/components/editor/cardNode'
import LinkCardView from './LinkCardView.vue'

export interface LinkCardAttrs {
  href: string
  title: string
  description?: string
  image?: string
  siteName?: string
  imageLayout?: 'large' | ''
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
      ...cardLinkAttributes(),
      description: dataAttribute('description'),
      image: dataAttribute('image'),
      siteName: dataAttribute('site-name'),
      imageLayout: dataAttribute('image-layout'),
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="link-card"]' }]
  },

  renderHTML: renderCard('link-card'),

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
