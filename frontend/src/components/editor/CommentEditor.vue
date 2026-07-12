<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { useIsMobile } from 'frappe-ui'
import GPEditor from './GPEditor.vue'
import CommentToolbarContent from './CommentToolbarContent.vue'
import MobileCommentToolbar from './MobileCommentToolbar.vue'
import QuoteReplyButton from '@/components/RichQuoteExtension/QuoteReplyButton.vue'
import { useRichQuotes, useBacklinkRefresh } from '@/components/RichQuoteExtension/useRichQuotes'
import { commentExtensions } from './commentExtensions'

// gameplan's comment box: the lighter CommentKit (no toc / iframe) + tables +
// @-mentions + #-tags + RichQuote + slash commands. The formatting buttons live in
// CommentToolbarContent, rendered inline below the editor on desktop and inside a
// keyboard-docked pill (MobileCommentToolbar) on mobile.
const props = withDefaults(
  defineProps<{
    value?: string
    placeholder?: string | null
    editable?: boolean
    submitButtonProps?: Record<string, any>
    discardButtonProps?: Record<string, any>
    maxHeight?: string
    minHeight?: string
    toolbarExpanded?: boolean
    // 'comment:<id>' — enables "quoted by" badges + Reply-to-quote on this comment
    // when it's rendered inside a discussion
    quoteSourceId?: string
    // comment owner — stamped on quotes created from this comment's selection
    author?: string
  }>(),
  { value: '', placeholder: null, editable: true, maxHeight: '50vh', toolbarExpanded: false },
)

const emit = defineEmits<{
  change: [value: string]
  'update:toolbarExpanded': [value: boolean]
}>()

const isMobile = useIsMobile()
const controller = useRichQuotes()

const extensions = commentExtensions({ controller, sourceId: props.quoteSourceId })

const gp = useTemplateRef<InstanceType<typeof GPEditor>>('gp')
const editor = computed(() => gp.value?.editor ?? null)

// Drives the mobile pill: it only appears while the editor holds focus, i.e. the
// keyboard is up for this composer.
const isFocused = ref(false)

useBacklinkRefresh(editor, props.quoteSourceId, () => props.editable ?? false)

defineExpose({ editor })
</script>

<template>
  <GPEditor
    ref="gp"
    :extensions="extensions"
    :content="value"
    :placeholder="placeholder ?? undefined"
    :editable="editable"
    :editor-class="['prose-v3 max-w-none relative', editable && 'min-h-[4rem]']"
    :max-height="editable ? maxHeight : undefined"
    :min-height="editable ? minHeight : undefined"
    @change="editable ? emit('change', $event) : null"
    @focus="isFocused = true"
    @blur="isFocused = false"
  >
    <template v-if="!editable && quoteSourceId" #top="{ editor: e }">
      <QuoteReplyButton v-if="e" :editor="e" :source-id="quoteSourceId" :author="author ?? ''" />
    </template>
    <template v-if="editable" #bottom="{ editor: e }">
      <div class="mt-2 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div v-if="!isMobile" class="flex min-w-0 items-center gap-1 overflow-x-auto">
          <CommentToolbarContent
            :editor="e"
            :toolbar-expanded="toolbarExpanded"
            @update:toolbar-expanded="emit('update:toolbarExpanded', $event)"
          />
        </div>
        <div class="flex items-center justify-between gap-2 sm:justify-end">
          <div class="sm:hidden">
            <slot name="actions-left" />
          </div>
          <div class="flex items-center justify-end space-x-2">
            <Button v-bind="discardButtonProps || {}"> Discard </Button>
            <Button variant="solid" v-bind="submitButtonProps || {}"> Submit </Button>
          </div>
        </div>
      </div>
      <MobileCommentToolbar
        v-if="isMobile"
        :editor="e"
        :toolbar-expanded="toolbarExpanded"
        :visible="isFocused"
        @update:toolbar-expanded="emit('update:toolbarExpanded', $event)"
      />
    </template>
  </GPEditor>
</template>
