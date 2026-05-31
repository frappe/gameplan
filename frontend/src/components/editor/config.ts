import type { Component } from 'vue'
import { useFileUpload } from 'frappe-ui'
import type { UploadedFile } from 'frappe-ui/editor'
import FloatingQuoteButton from '@/components/RichQuoteExtension/floating-quote-button'
import RichQuoteNodeExtension from '@/components/RichQuoteExtension/rich-quote-node-extension'
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
 * gameplan-local RichQuote extensions, appended after the kit (spec §6). The
 * handlers re-emit so the host component can surface `@rich-quote` /
 * `@rich-quote-click`, exactly as the old wrapper did.
 */
export function richQuoteExtensions(handlers: {
  onQuote: (html: string) => void
  onQuoteClick: (payload: {
    quoteId: string
    author: string
    content: string
  }) => void
}) {
  return [
    FloatingQuoteButton.configure({ onClick: handlers.onQuote }),
    RichQuoteNodeExtension.configure({ onClick: handlers.onQuoteClick }),
  ]
}

/**
 * The frappe file upload the v0 monolith invoked silently as its default. v1's
 * editor requires an explicit `uploadFunction`, so gameplan passes this one.
 */
export function uploadFile(file: File): Promise<UploadedFile> {
  return useFileUpload().upload(file, {})
}
