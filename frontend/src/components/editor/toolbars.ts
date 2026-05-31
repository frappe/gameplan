import {
  Bold,
  Italic,
  Strike,
  InlineCode,
  BulletList,
  OrderedList,
  Blockquote,
  Paragraph,
  H2,
  H3,
  H4,
  AlignLeft,
  AlignCenter,
  AlignRight,
  FontColor,
  InsertImage,
  InsertVideo,
  InsertLink,
  InsertTable,
  HorizontalRule,
  Separator,
  Undo,
  Redo,
  type MenuItem,
} from 'frappe-ui/editor'

// The predefined items ship their own default icons from frappe-ui, so this is
// just composition — no per-item icon plumbing.
//
// The single gameplan toolbar, replacing the duplicated `textEditorMenuButtons`
// arrays. Self-pruning (spec §5): in a CommentKit editor the table / align / color
// buttons hide automatically because those extensions aren't loaded, so the same
// array serves the comment box and the rich (RichTextKit) editors alike.
export const gameplanToolbar: MenuItem[] = [
  Paragraph,
  H2,
  H3,
  H4,
  Separator,
  Bold,
  Italic,
  Strike,
  Separator,
  BulletList,
  OrderedList,
  Separator,
  AlignLeft,
  AlignCenter,
  AlignRight,
  FontColor,
  Separator,
  InsertImage,
  InsertVideo,
  InsertLink,
  Blockquote,
  InlineCode,
  HorizontalRule,
  Separator,
  InsertTable,
  Separator,
  Undo,
  Redo,
]

/** Block-insert menu shown on empty lines (Notion-style "+"): block affordances only. */
export const gameplanFloatingToolbar: MenuItem[] = [
  Paragraph,
  H2,
  H3,
  BulletList,
  OrderedList,
  Blockquote,
  InlineCode,
  HorizontalRule,
]
