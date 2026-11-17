<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import GPEditor from './GPEditor.vue'
import QuoteReplyButton from '@/components/RichQuoteExtension/QuoteReplyButton.vue'
import { useRichQuotes, useBacklinkRefresh } from '@/components/RichQuoteExtension/useRichQuotes'
import { gameplanToolbar } from './toolbars'
import { commentExtensions } from './commentExtensions'

// The editor for a discussion's main post (GP Discussion content). One scenario,
// composed directly from GPEditor — not a configurable generic:
//   - read mode: renders the post body with a quote-reply bubble
//   - edit mode: a free-growing body (no inner scroll) with a selection bubble
//     menu. Save and Discard live in the post header (DiscussionView).
// Other surfaces (comments, pages, tasks) get their own dedicated editor rather
// than another prop on a shared one.
const props = withDefaults(
  defineProps<{
    content?: string
    editable?: boolean
    // 'discussion:<id>' — powers the "quoted by" backlink badges + Reply-to-quote
    quoteSourceId: string
    // post owner — stamped on quotes created from this post's selection
    author?: string
  }>(),
  { content: '', editable: false },
)

const emit = defineEmits<{
  change: [value: string]
}>()

const controller = useRichQuotes()

const extensions = commentExtensions({ controller, sourceId: props.quoteSourceId })

const gp = useTemplateRef<InstanceType<typeof GPEditor>>('gp')
const editor = computed(() => gp.value?.editor ?? null)

useBacklinkRefresh(editor, props.quoteSourceId, () => props.editable ?? false)

defineExpose({ editor })
</script>

<template>
  <GPEditor
    ref="gp"
    :extensions="extensions"
    :content="content"
    :editable="editable"
    :editor-class="['prose-v3 max-w-none relative', editable && 'min-h-[4rem]']"
    :bubble-menu="editable ? gameplanToolbar : false"
    @change="editable ? emit('change', $event) : null"
  >
    <template v-if="!editable" #top="{ editor: e }">
      <QuoteReplyButton v-if="e" :editor="e" :source-id="quoteSourceId" :author="author ?? ''" />
    </template>
  </GPEditor>
</template>
