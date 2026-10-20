import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import PollBlockView from './PollBlockView.vue'
import { emptyPollDraft, parseDraft } from './poll-draft'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    pollBlock: {
      insertPollBlock: () => ReturnType
    }
  }
}

export const PollBlockExtension = Node.create({
  name: 'pollBlock',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      poll: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-poll'),
        renderHTML: (attributes) => (attributes.poll ? { 'data-poll': attributes.poll } : {}),
      },
      draft: {
        default: null,
        parseHTML: (element) => parseDraft(element.getAttribute('data-poll-draft')),
        renderHTML: (attributes) =>
          attributes.draft ? { 'data-poll-draft': JSON.stringify(attributes.draft) } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="poll"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-type': 'poll' }, HTMLAttributes)]
  },

  addNodeView() {
    return VueNodeViewRenderer(PollBlockView)
  },

  addCommands() {
    return {
      insertPollBlock:
        () =>
        ({ commands }) =>
          commands.insertContent([
            { type: this.name, attrs: { draft: emptyPollDraft() } },
            { type: 'paragraph' },
          ]),
    }
  },
})

export default PollBlockExtension
