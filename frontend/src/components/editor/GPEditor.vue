<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef, watch, type CSSProperties } from 'vue'
import type { AnyExtension } from '@tiptap/core'
import {
  Editor as FrappeEditor,
  EditorContent,
  EditorDropZone,
  EditorFixedMenu,
  EditorBubbleMenu,
  EditorTableMenu,
  EditorFloatingMenu,
  type MenuItem,
} from 'frappe-ui/editor'
import { uploadFile } from './config'

// Shared gameplan editor layout, built on the v1 <Editor> via its #default
// (L3) slot so gameplan keeps full control of editor-class, the scroll container,
// and menu placement. Kit-free on purpose: callers pass `extensions` (kit +
// mentions + RichQuote), which keeps CommentKit and RichTextKit in separate route
// chunks instead of forcing both into every editor's bundle.
const props = withDefaults(
  defineProps<{
    extensions: AnyExtension[]
    content?: string | null
    placeholder?: string
    editable?: boolean
    autofocus?: boolean
    editorClass?: unknown
    maxHeight?: string
    minHeight?: string
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

const ft = useTemplateRef<InstanceType<typeof FrappeEditor>>('ft')
const editorContent = useTemplateRef<HTMLElement>('editorContent')
const editor = computed(() => ft.value?.editor ?? null)
const hasScrollOverflow = ref(false)
const canScrollUp = ref(false)
const canScrollDown = ref(false)
const showScrollFades = computed(() => Boolean(props.maxHeight && !props.editable))

const scrollStyle = computed<CSSProperties>(() => ({
  maxHeight: props.maxHeight,
  minHeight: props.minHeight,
  overflowY: props.maxHeight ? 'auto' : undefined,
}))

watch(
  () => [props.content, props.editable, props.maxHeight, props.minHeight],
  () => nextTick(updateScrollFades),
  { immediate: true },
)

defineExpose({ editor })

function updateScrollFades() {
  const $el = editorContent.value?.$el ?? editorContent.value
  if (!$el) return

  hasScrollOverflow.value = $el.scrollHeight > $el.clientHeight + 1
  canScrollUp.value = hasScrollOverflow.value && $el.scrollTop > 1
  canScrollDown.value =
    hasScrollOverflow.value && $el.scrollTop + $el.clientHeight < $el.scrollHeight - 1
}
</script>

<template>
  <FrappeEditor
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
      <EditorTableMenu :editor="e" />
      <EditorFloatingMenu v-if="floatingMenu" :editor="e" :items="floatingMenu" />
      <EditorFixedMenu
        v-if="fixedMenu && fixedMenuPosition === 'top'"
        :editor="e"
        :items="fixedMenu"
        class="overflow-x-auto"
      />
      <slot name="editor" :editor="e" :editor-class="editorClass" :scroll-style="scrollStyle">
        <EditorDropZone
          :editor="e"
          :disabled="!editable"
          class="relative"
          :class="{
            'before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:z-10 before:h-8 before:bg-gradient-to-b before:from-surface-base before:to-transparent before:opacity-0 before:transition-opacity before:duration-150':
              showScrollFades,
            'after:pointer-events-none after:absolute after:inset-x-0 after:bottom-0 after:z-10 after:h-8 after:bg-gradient-to-t after:from-surface-base after:to-transparent after:opacity-0 after:transition-opacity after:duration-150':
              showScrollFades,
            'before:opacity-100': canScrollUp,
            'after:opacity-100': canScrollDown,
          }"
        >
          <EditorContent
            ref="editorContent"
            :editor="e"
            :class="editorClass"
            :style="scrollStyle"
            @scroll="updateScrollFades"
          />
        </EditorDropZone>
      </slot>
      <EditorFixedMenu
        v-if="fixedMenu && fixedMenuPosition === 'bottom'"
        :editor="e"
        :items="fixedMenu"
        class="overflow-x-auto"
      />
      <slot name="bottom" :editor="e" :is-empty="isEmpty" />
    </template>
  </FrappeEditor>
</template>
