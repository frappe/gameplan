import type { MenuItem } from 'frappe-ui/editor'
import type { Editor } from '@tiptap/core'
import { hasPollBlock } from './poll-draft'

const hasPollNode = (editor: Editor) => 'pollBlock' in editor.schema.nodes

/**
 * Toolbar entry that writes a poll into the post, as the reply box's Poll button does. A
 * post holds one poll, so it is disabled once the post has one. Hides itself in an editor
 * without the poll node.
 */
export const InsertPoll: MenuItem = {
  label: 'Poll',
  icon: 'lucide-bar-chart-2',
  action: (editor) => {
    editor.chain().focus().insertPollBlock().run()
  },
  isDisabled: hasPollBlock,
  isAvailable: hasPollNode,
}
