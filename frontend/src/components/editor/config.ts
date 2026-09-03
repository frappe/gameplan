import type { Component } from 'vue'
import type { AnyExtension } from '@tiptap/core'
import { useFileUpload } from 'frappe-ui'
import { Mention, type MediaUploadRequestOptions, type UploadedFile } from 'frappe-ui/editor'

export const ALLOWED_MENTION_PREFIXES = [' ', '(', '\\[', '{', '<', '（', '【', '《', '"', "'"]

const origAddExtensions = Mention.config.addExtensions
Mention.config.addExtensions = function () {
  const extensions = origAddExtensions ? origAddExtensions.call(this) : []
  return extensions.map((ext: any) => {
    if (ext.name === 'mentionSuggestion') {
      return ext.configure({
        suggestion: {
          allowedPrefixes: ALLOWED_MENTION_PREFIXES,
        },
      })
    }
    return ext
  })
}
import RichQuoteNodeExtension from '@/components/RichQuoteExtension/rich-quote-node-extension'
import QuoteBacklinkDecoration from '@/components/RichQuoteExtension/quote-backlink-decoration'
import type { RichQuoteController } from '@/components/RichQuoteExtension/useRichQuotes'
import TextEditorMentionComponent from '@/components/TextEditorMentionComponent.vue'
import { activeUsers } from '@/data/users'
import { tags as tagList } from '@/data/tags'

// @-mention items: gameplan users plus an "Everyone" entry. The mention node stores
// `id`/`label`; the suggestion command maps value→id, so we provide all three.
function mentionItems() {
  return [{ id: '_everyone_', label: 'Everyone', value: '_everyone_' }].concat(
    activeUsers.value.map((user) => ({
      id: user.name,
      label: user.full_name.trimEnd(),
      value: user.name,
    })),
  )
}

function tagItems() {
  return (tagList.data ?? []).map((tag) => ({ id: tag.name, label: tag.label }))
}

/**
 * gameplan drops H1 everywhere — kits are configured with these heading levels.
 * Kept here (kit-free) so both extension stacks share one source of truth.
 */
export const gameplanHeadingLevels = [2, 3, 4, 5, 6] as const

/**
 * Kit-member config for @-mentions + #-tags, applied via `kit.configure(...)`
 * (spec §3 — data-driven members configured, never proxied through props). Passing
 * getters keeps the live user/tag lists reactive. `suggestions: false` keeps the
 * nodes (so existing mentions/tags still render) but disables the live popups —
 * used by Pages, which never had them.
 */
export function suggestionConfig(suggestions = true) {
  return {
    mention: {
      items: suggestions ? mentionItems : null,
      component: TextEditorMentionComponent as Component,
    },
    tag: { items: suggestions ? tagItems : null },
  }
}

/**
 * gameplan-local RichQuote extensions, appended after the kit (spec §6).
 *
 * Both the inserted quote's click handler and the "quoted by" badges talk to the
 * single RichQuoteController directly — no event re-emitting. Pass the controller
 * (and the surface's `sourceId`) inside a discussion; omit it for rich editors
 * outside one (Pages/Tasks), where quotes still render but aren't interactive.
 * The floating Reply button is a component (QuoteReplyButton.vue), not an extension.
 */
export function richQuoteExtensions(controller?: RichQuoteController | null, sourceId?: string) {
  const extensions: AnyExtension[] = [
    RichQuoteNodeExtension.configure({
      onClick: controller ? (payload) => controller.navigateToQuote(payload) : () => {},
    }),
  ]
  if (controller && sourceId) {
    extensions.push(
      QuoteBacklinkDecoration.configure({
        getBacklinks: () => controller.getFor(sourceId),
        onBacklinkClick: ({ anchorEl, items }) => controller.openPopover(anchorEl, items),
      }),
    )
  }
  return extensions
}

/**
 * The frappe file upload the v0 monolith invoked silently as its default. v1's
 * editor requires an explicit `uploadFunction`, so gameplan passes this one.
 *
 * Uploads default to `private: true` so editor images/attachments are not served
 * from the unauthenticated `/files/` path (frappe/security#206). The backend
 * attaches each file to its parent doc on save (see gameplan/mixins/attachments.py),
 * which is what lets other space members read the now-private file. The runtime
 * `{ signal, onProgress }` the editor engine passes is preserved.
 */
export function uploadFile(file: File, options?: MediaUploadRequestOptions): Promise<UploadedFile> {
  return useFileUpload().upload(file, { private: true, ...(options ?? {}) })
}
