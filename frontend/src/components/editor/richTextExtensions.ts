import { RichTextKit } from 'frappe-ui/editor'
import { gameplanHeadingLevels, suggestionConfig, richQuoteExtensions } from './config'
import { collapsibleExtensions, slashCommandsWithCollapsible } from './collapsible'

/**
 * The rich extension stack (articles, pages, discussion bodies, task descriptions):
 * RichTextKit + @-mentions + #-tags + RichQuote. Specialized wrappers compose this
 * instead of repeating the `RichTextKit.configure(...)` block. `suggestions: false`
 * keeps mention/tag nodes rendering but disables the live popups (used by Pages).
 *
 * Kept in its own module (not config.ts) so RichTextKit stays out of the kit-free
 * GPEditor chunk and only loads on routes that use a rich editor.
 */
export function richTextExtensions(opts: { suggestions?: boolean } = {}) {
  return [
    RichTextKit.configure({
      heading: { levels: [...gameplanHeadingLevels] },
      table: { cellMinWidth: 25 },
      // The kit's stock slash registry is replaced by the same registry plus the
      // gameplan-only "Collapsible section" command.
      slashCommands: false,
      ...suggestionConfig(opts.suggestions ?? true),
    }),
    slashCommandsWithCollapsible(),
    ...collapsibleExtensions(),
    ...richQuoteExtensions(),
  ]
}
