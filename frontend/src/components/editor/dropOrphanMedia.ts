import { Extension } from '@tiptap/core'
import { Plugin, PluginKey, type EditorState, type Transaction } from '@tiptap/pm/state'
import type { Fragment, Node as PMNode } from '@tiptap/pm/model'
import { ReplaceAroundStep, ReplaceStep } from '@tiptap/pm/transform'

const MEDIA_NODES = new Set(['image', 'video'])

/**
 * An image or video with no `src` and no `uploadId` is an upload that never finished.
 *
 * While an upload runs, or after it fails, the node carries an `uploadId`, and the editor
 * shows its progress or its error with "Try again". frappe-ui does not write `uploadId`,
 * `loading` or `error` to HTML, so the saved copy of that node is a bare `<video>`. Loaded
 * again (a reload, a restored draft, the published post), it parses with no `uploadId`
 * and frappe-ui draws "This video hasn't yet been uploaded." with nothing to retry.
 */
function isOrphan(node: PMNode, parent: PMNode | null): boolean {
  return (
    MEDIA_NODES.has(node.type.name) &&
    !node.attrs.src &&
    !node.attrs.uploadId &&
    // An image group needs at least one image; it only ever holds uploaded ones.
    parent?.type.name !== 'imageGroup'
  )
}

function containsOrphan(fragment: Fragment): boolean {
  let found = false
  fragment.descendants((node, _pos, parent) => {
    if (found) return false
    found = isOrphan(node, parent)
    return !found
  })
  return found
}

function removeOrphans(state: EditorState): Transaction | null {
  const ranges: Array<[number, number]> = []
  state.doc.descendants((node, pos, parent) => {
    if (isOrphan(node, parent)) ranges.push([pos, pos + node.nodeSize])
  })
  if (!ranges.length) return null
  const tr = state.tr
  for (const [from, to] of ranges.reverse()) tr.delete(from, to)
  // A cleanup of loaded content, not an edit: keep it out of undo and out of `change`.
  return tr.setMeta('addToHistory', false).setMeta('preventUpdate', true)
}

/**
 * Drops unfinished uploads from content loaded from HTML, so a failed or interrupted
 * upload never comes back as an empty placeholder. Uploads in this session keep their
 * `uploadId` and are left alone.
 *
 * Remove once frappe-ui stops writing unfinished media to HTML (upstream fix not yet
 * opened; see the PR for this change).
 */
export const DropOrphanMedia = Extension.create({
  name: 'dropOrphanMedia',

  onCreate() {
    const tr = removeOrphans(this.editor.state)
    if (tr) this.editor.view.dispatch(tr)
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('dropOrphanMedia'),
        // Only inspect what the transactions inserted, so typing stays cheap.
        appendTransaction: (transactions, _oldState, newState) => {
          const inserted = transactions.some((tr) =>
            tr.steps.some(
              (step) =>
                (step instanceof ReplaceStep || step instanceof ReplaceAroundStep) &&
                containsOrphan(step.slice.content),
            ),
          )
          return inserted ? removeOrphans(newState) : null
        },
      }),
    ]
  },
})
