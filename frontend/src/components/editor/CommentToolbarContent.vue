<script setup lang="ts">
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
import { computed } from 'vue'

// The formatting buttons for the comment composer. Extracted from CommentEditor
// so the same button set renders both inline (desktop, below the editor) and in
// the mobile pill toolbar that docks above the keyboard — one source of truth.
const props = defineProps<{
  editor: Editor
  toolbarExpanded: boolean
}>()

const emit = defineEmits<{
  'update:toolbarExpanded': [value: boolean]
}>()

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
  <template v-if="toolbarExpanded">
    <EditorFixedMenu
      :editor="editor"
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
        @click="openSlashCommands(editor)"
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
        @click="insertTrigger(editor, '@')"
      />
      <EmojiPicker @select="insertEmoji(editor, $event)">
        <template #trigger>
          <Button size="sm" variant="ghost" icon="lucide-smile" label="Emoji" tooltip="Emoji" />
        </template>
      </EmojiPicker>
      <span class="mx-1 h-5 border-l border-outline-gray-2" aria-hidden="true" />
      <Button
        size="sm"
        variant="ghost"
        icon="lucide-image"
        label="Image"
        tooltip="Image"
        :disabled="!canInsertImage(editor)"
        @click="insertImage(editor)"
      />
      <Button
        size="sm"
        variant="ghost"
        icon="lucide-video"
        label="Video"
        tooltip="Video"
        :disabled="!canInsertVideo(editor)"
        @click="insertVideo(editor)"
      />
      <Button
        size="sm"
        variant="ghost"
        icon="lucide-paperclip"
        label="Attach"
        tooltip="Attach file"
        :disabled="!canInsertAttachment(editor)"
        @click="insertAttachment(editor)"
      />
      <Button
        size="sm"
        variant="ghost"
        icon="lucide-code"
        label="Code block"
        tooltip="Code block"
        :disabled="!canInsertCodeBlock(editor)"
        @click="insertCodeBlock(editor)"
      />
    </TooltipProvider>
  </template>
</template>
