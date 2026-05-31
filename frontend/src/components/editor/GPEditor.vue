<script setup lang="ts">
import { computed, useTemplateRef, type CSSProperties } from 'vue'
import type { Extension } from '@tiptap/core'
import {
  TextEditor as FTextEditor,
  EditorContent,
  EditorFixedMenu,
  EditorBubbleMenu,
  EditorFloatingMenu,
  type MenuItem,
} from 'frappe-ui/editor'
import { uploadFile } from './config'

// Shared gameplan editor layout, built on the v1 <TextEditor> via its #default
// (L3) slot so gameplan keeps full control of editor-class, the scroll container,
// and menu placement. Kit-free on purpose: callers pass `extensions` (kit +
// mentions + RichQuote), which keeps CommentKit and RichTextKit in separate route
// chunks instead of forcing both into every editor's bundle.
const props = withDefaults(
  defineProps<{
    extensions: Extension[]
    content?: string | null
    placeholder?: string
    editable?: boolean
    autofocus?: boolean
    editorClass?: unknown
    maxHeight?: string
    fixedMenu?: MenuItem[] | false
    fixedMenuPosition?: 'top' | 'bottom'
    bubbleMenu?: MenuItem[] | false
    floatingMenu?: MenuItem[] | false
  }>(),
  {
    editable: true,
    autofocus: false,
    fixedMenu: false,
    fixedMenuPosition: 'bottom',
    bubbleMenu: false,
    floatingMenu: false,
  },
)

const emit = defineEmits<{
  change: [value: string]
  blur: [event: FocusEvent]
  focus: [event: FocusEvent]
}>()

const ft = useTemplateRef<InstanceType<typeof FTextEditor>>('ft')
const editor = computed(() => ft.value?.editor ?? null)

const scrollStyle = computed<CSSProperties>(() => ({
  maxHeight: props.maxHeight,
  overflowY: props.maxHeight ? 'auto' : undefined,
}))

defineExpose({ editor })
</script>

<template>
  <FTextEditor
    ref="ft"
    :extensions="extensions"
    :model-value="content ?? ''"
    :editable="editable"
    :autofocus="autofocus"
    :placeholder="placeholder"
    :upload-function="uploadFile"
    @change="emit('change', $event as string)"
    @blur="emit('blur', $event)"
    @focus="emit('focus', $event)"
  >
    <template #default="{ editor: e, isEmpty }">
      <slot name="top" :editor="e" />
      <EditorBubbleMenu v-if="bubbleMenu" :editor="e" :items="bubbleMenu" />
      <EditorFloatingMenu v-if="floatingMenu" :editor="e" :items="floatingMenu" />
      <EditorFixedMenu
        v-if="fixedMenu && fixedMenuPosition === 'top'"
        :editor="e"
        :items="fixedMenu"
        class="overflow-x-auto"
      />
      <slot name="editor" :editor="e">
        <EditorContent :editor="e" :class="editorClass" :style="scrollStyle" />
      </slot>
      <EditorFixedMenu
        v-if="fixedMenu && fixedMenuPosition === 'bottom'"
        :editor="e"
        :items="fixedMenu"
        class="overflow-x-auto"
      />
      <slot name="bottom" :editor="e" :is-empty="isEmpty" />
    </template>
  </FTextEditor>
</template>
