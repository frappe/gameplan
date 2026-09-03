import {
  CommentKit,
  TaskList,
  TaskItem,
  Iframe,
  Toc,
  TextStyle,
  Color,
  Highlight,
} from 'frappe-ui/editor'
import { gameplanHeadingLevels, suggestionConfig, richQuoteExtensions } from './config'
import { collapsibleExtensions, slashCommandsWithCollapsible } from './collapsible'
import { CustomEmojiExtension } from './customEmojiExtension'
import type { RichQuoteController } from '@/components/RichQuoteExtension/useRichQuotes'

/**
 * The comment stack: CommentKit + tables + task lists + embeds + table of
 * contents + @-mentions + #-tags + RichQuote + slash commands. Used by
 * CommentEditor — which also renders the discussion post body — so blocks
 * created while composing a discussion (RichTextKit) render and edit here too.
 *
 * SlashCommands self-prunes via each command's `isAvailable` predicate, so the
 * "/" menu only offers what the loaded schema supports. We layer task-list /
 * iframe / toc onto CommentKit (a lighter kit that omits them) so the comment
 * box and the discussion post body get the SAME slash menu as the discussion
 * compose editor (richTextExtensions) — otherwise editing a saved post loses
 * the task-list / embed / table-of-contents commands it was composed with.
 *
 * Kept in its own module (not config.ts) so CommentKit only loads in the comment
 * box chunk, never in the rich-editor or shared GPEditor chunks.
 */
export function commentExtensions(
  opts: { controller?: RichQuoteController | null; sourceId?: string } = {},
) {
  return [
    CommentKit.configure({
      heading: { levels: [...gameplanHeadingLevels] },
      table: { cellMinWidth: 25 },
      ...suggestionConfig(true),
    }),
    // TaskItem requires TaskList; Iframe ships the `openIframeDialog` command and
    // Toc the `tocNode` — each unlocks its matching "/" command via isAvailable.
    TaskList,
    TaskItem,
    Iframe,
    Toc,
    // Color writes a `color` attribute onto the TextStyle mark (no node of its
    // own), so the two register together — this is what unlocks the FontColor
    // toolbar button (isAvailable: hasExtension('namedColor')). Highlight backs
    // the picker's second column (text + highlight), whose setHighlight path
    // calls toggleHighlightByName — without it the picker throws.
    TextStyle,
    Color,
    Highlight,
    CustomEmojiExtension,
    // Collapsible sections load here too, so a section written in a discussion
    // body still renders and edits when that body is reopened in CommentEditor.
    ...collapsibleExtensions(),
    slashCommandsWithCollapsible(),
    ...richQuoteExtensions(opts.controller, opts.sourceId),
  ]
}
