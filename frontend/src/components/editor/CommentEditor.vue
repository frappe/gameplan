<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { Button, TooltipProvider } from 'frappe-ui'
import {
  Blockquote,
  Bold,
  BulletList,
  EditorFixedMenu,
  FontColor,
  H2,
  H3,
  H4,
  InsertLink,
  Italic,
  OrderedList,
  Paragraph,
  Separator,
  Strike,
  type Editor,
  type MenuItem,
} from 'frappe-ui/editor'
import EmojiPicker from '@/components/EmojiPicker.vue'
import { isImageEmoji } from '@/utils/emoji'
import GPEditor from './GPEditor.vue'
import QuoteReplyButton from '@/components/RichQuoteExtension/QuoteReplyButton.vue'
import { useRichQuotes, useBacklinkRefresh } from '@/components/RichQuoteExtension/useRichQuotes'
import { commentExtensions } from './commentExtensions'

// gameplan's comment box: the lighter CommentKit (no toc / iframe) + tables +
// @-mentions + #-tags + RichQuote + slash commands. The shared `gameplanToolbar`
// self-prunes to the comment-available buttons (spec §5), so it needs no separate
// curation.
const props = withDefaults(
  defineProps<{
    value?: string
    placeholder?: string | null
    editable?: boolean
    submitButtonProps?: Record<string, any>
    discardButtonProps?: Record<string, any>
    // Unset on purpose: the editor grows to its content by default, so editing an
    // existing comment reads like editing a post body instead of a fixed box that
    // scrolls internally. Only the new-comment composers pass a max-height — they
    // sit at the bottom of a scrolling list, so an unbounded box would push the
    // conversation off screen as you type. Don't reinstate a default here: a caller
    // cannot opt out of one, since withDefaults substitutes it for an explicit
    // `undefined`.
    maxHeight?: string
    minHeight?: string
    toolbarExpanded?: boolean
    // 'comment:<id>' — enables "quoted by" badges + Reply-to-quote on this comment
    // when it's rendered inside a discussion
    quoteSourceId?: string
    // comment owner — stamped on quotes created from this comment's selection
    author?: string
  }>(),
  { value: '', placeholder: null, editable: true, toolbarExpanded: false },
)

const emit = defineEmits<{
  change: [value: string]
  'update:toolbarExpanded': [value: boolean]
}>()

const controller = useRichQuotes()

const extensions = commentExtensions({ controller, sourceId: props.quoteSourceId })

const gp = useTemplateRef<InstanceType<typeof GPEditor>>('gp')
const editor = computed(() => gp.value?.editor ?? null)
const expandedToolbarItems = computed<MenuItem[]>(() => [
  insertItem,
  textToolsItem,
  Separator,
  Paragraph,
  H2,
  H3,
  H4,
  Separator,
  Bold,
  Italic,
  Strike,
  FontColor,
  Separator,
  BulletList,
  OrderedList,
  Blockquote,
  Separator,
  InsertLink,
])

useBacklinkRefresh(editor, props.quoteSourceId, () => props.editable ?? false)

defineExpose({ editor })

function hasEditorCommand(editor: Editor, command: string) {
  return typeof (editor.commands as Record<string, unknown>)[command] === 'function'
}

// Mirrors the collapsed "+" Insert button so it keeps the same slot when the
// toolbar expands — otherwise the Text tools toggle shifts left and feels unstable.
const insertItem: MenuItem = {
  label: 'Insert',
  icon: 'lucide-plus',
  action: (editor) => openSlashCommands(editor),
}

const textToolsItem: MenuItem = {
  label: 'Text tools',
  icon: 'lucide-case-sensitive',
  getLabel: () => (props.toolbarExpanded ? 'Hide text tools' : 'Show text tools'),
  action: () => emit('update:toolbarExpanded', !props.toolbarExpanded),
  isActive: () => props.toolbarExpanded,
}

function openSlashCommands(editor: Editor) {
  editor.chain().focus().insertContent(' /').run()
}

function insertTrigger(editor: Editor, trigger: '@') {
  editor.chain().focus().insertContent(` ${trigger}`).run()
}

function insertEmoji(editor: Editor, emoji: string) {
  // Custom emoji are image URLs — insert them via the inline customEmoji node so
  // they sit in the text at ~20px, instead of the block image node (which adds
  // resize/viewer chrome and centers on its own line).
  if (isImageEmoji(emoji)) {
    editor.chain().focus().insertCustomEmoji({ src: emoji, alt: 'emoji' }).run()
  } else {
    editor.chain().focus().insertContent(emoji).run()
  }
}

function insertImage(editor: Editor) {
  if (canInsertImage(editor)) editor.chain().focus().selectAndUploadImage().run()
}

function insertVideo(editor: Editor) {
  if (canInsertVideo(editor)) editor.chain().focus().selectAndUploadVideo().run()
}

function insertAttachment(editor: Editor) {
  if (canInsertAttachment(editor)) editor.chain().focus().selectAndUploadFile().run()
}

function insertCodeBlock(editor: Editor) {
  if (canInsertCodeBlock(editor)) editor.chain().focus().toggleCodeBlock().run()
}

function canInsertImage(editor: Editor) {
  return 'image' in editor.schema.nodes && hasEditorCommand(editor, 'selectAndUploadImage')
}

function canInsertVideo(editor: Editor) {
  return 'video' in editor.schema.nodes && hasEditorCommand(editor, 'selectAndUploadVideo')
}

function canInsertAttachment(editor: Editor) {
  return 'attachment' in editor.schema.nodes && hasEditorCommand(editor, 'selectAndUploadFile')
}

function canInsertCodeBlock(editor: Editor) {
  return 'codeBlock' in editor.schema.nodes
}
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
  >
    <template v-if="!editable && quoteSourceId" #top="{ editor: e }">
      <QuoteReplyButton v-if="e" :editor="e" :source-id="quoteSourceId" :author="author ?? ''" />
    </template>
    <template v-if="editable" #bottom="{ editor: e }">
      <div class="mt-2 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div class="flex min-w-0 items-center gap-1 overflow-x-auto">
          <template v-if="toolbarExpanded">
            <EditorFixedMenu
              :editor="e"
              :items="expandedToolbarItems"
              button-size="sm"
              class="overflow-x-auto"
            />
          </template>
          <template v-else>
            <TooltipProvider>
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-plus"
                label="Insert"
                tooltip="Insert"
                @click="openSlashCommands(e)"
              />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-case-sensitive"
                label="Text tools"
                tooltip="Text tools"
                @click="emit('update:toolbarExpanded', true)"
              />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-at-sign"
                label="Mention"
                tooltip="Mention"
                @click="insertTrigger(e, '@')"
              />
              <EmojiPicker @select="insertEmoji(e, $event)">
                <template #trigger>
                  <Button
                    size="sm"
                    variant="ghost"
                    icon="lucide-smile"
                    label="Emoji"
                    tooltip="Emoji"
                  />
                </template>
              </EmojiPicker>
              <span class="mx-1 h-5 border-l border-outline-gray-2" aria-hidden="true" />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-image"
                label="Image"
                tooltip="Image"
                :disabled="!canInsertImage(e)"
                @click="insertImage(e)"
              />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-video"
                label="Video"
                tooltip="Video"
                :disabled="!canInsertVideo(e)"
                @click="insertVideo(e)"
              />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-paperclip"
                label="Attach"
                tooltip="Attach file"
                :disabled="!canInsertAttachment(e)"
                @click="insertAttachment(e)"
              />
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-code"
                label="Code block"
                tooltip="Code block"
                :disabled="!canInsertCodeBlock(e)"
                @click="insertCodeBlock(e)"
              />
            </TooltipProvider>
          </template>
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
    </template>
  </GPEditor>
</template>
