import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import Component from './Component.vue'

export default Node.create({
  name: 'team-task',
  group: 'block',
  atom: true,
  addAttributes() {
    return {
      taskId: {
        default: 0,
        parseHTML: (element) => element.getAttribute('task-id'),
      },
    }
  },
  parseHTML() {
    return [
      {
        tag: 'team-task',
      },
    ]
  },
  renderHTML({ HTMLAttributes }) {
    return ['team-task', mergeAttributes(HTMLAttributes)]
  },
  addNodeView() {
    return VueNodeViewRenderer(Component)
  },
  addCommands() {
    return {
      insertTask:
        (options) =>
        ({ chain, editor }) => {
          const { selection } = editor.state
          const pos = selection.$head

          return chain()
            .insertContentAt(pos.before(), [
              {
                type: this.name,
                attrs: { taskId: 'new' },
              },
            ])
            .run()
        },
    }
  },
})
