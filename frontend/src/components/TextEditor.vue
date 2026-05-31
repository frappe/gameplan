<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { RichTextKit, type MenuItem } from 'frappe-ui/editor'
import GPEditor from './editor/GPEditor.vue'
import { gameplanToolbar, gameplanFloatingToolbar } from './editor/toolbars'
import { suggestionConfig, richQuoteExtensions } from './editor/config'

// gameplan's rich editor (articles, pages, discussion bodies, task descriptions):
// RichTextKit + @-mentions + #-tags + the local RichQuote extensions. This is the
// app's thin component on <TextEditor> (ADR-0004 §"Apps own their editor
// components"); comments use the lighter CommentKit via CommentEditor.vue.
const props = withDefaults(
  defineProps<{
    content?: string | null
    placeholder?: string
    editable?: boolean
    autofocus?: boolean
    editorClass?: unknown
    maxHeight?: string
    suggestions?: boolean
    fixedMenu?: MenuItem[] | boolean
    fixedMenuPosition?: 'top' | 'bottom'
    bubbleMenu?: MenuItem[] | boolean
    floatingMenu?: MenuItem[] | boolean
  }>(),
  {
    editable: true,
    suggestions: true,
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
  'rich-quote': [html: string]
  'rich-quote-click': [payload: { quoteId: string; author: string; content: string }]
}>()

const extensions = computed(() => [
  RichTextKit.configure({
    // gameplan drops H1 everywhere (was :starterkit-options="{ heading… }").
    heading: { levels: [2, 3, 4, 5, 6] },
    ...suggestionConfig(props.suggestions),
  }),
  ...richQuoteExtensions({
    onQuote: (html) => emit('rich-quote', html),
    onQuoteClick: (payload) => emit('rich-quote-click', payload),
  }),
])

// `true` selects gameplan's default preset (v0's `:bubble-menu="true"` ergonomics);
// an array passes through; `false` hides the surface.
function resolve(menu: MenuItem[] | boolean, preset: MenuItem[]): MenuItem[] | false {
  if (menu === true) return preset
  if (menu === false) return false
  return menu
}
const fixedMenu = computed(() => resolve(props.fixedMenu, gameplanToolbar))
const bubbleMenu = computed(() => resolve(props.bubbleMenu, gameplanToolbar))
const floatingMenu = computed(() => resolve(props.floatingMenu, gameplanFloatingToolbar))

const gp = useTemplateRef<InstanceType<typeof GPEditor>>('gp')
const editor = computed(() => gp.value?.editor ?? null)
defineExpose({ editor })
</script>

<template>
  <GPEditor
    ref="gp"
    :extensions="extensions"
    :content="content"
    :placeholder="placeholder"
    :editable="editable"
    :autofocus="autofocus"
    :editor-class="editorClass"
    :max-height="maxHeight"
    :fixed-menu="fixedMenu"
    :fixed-menu-position="fixedMenuPosition"
    :bubble-menu="bubbleMenu"
    :floating-menu="floatingMenu"
    @change="emit('change', $event)"
    @blur="emit('blur', $event)"
    @focus="emit('focus', $event)"
  >
    <template v-if="$slots.top" #top="slotProps">
      <slot name="top" v-bind="slotProps" />
    </template>
    <template v-if="$slots.editor" #editor="slotProps">
      <slot name="editor" v-bind="slotProps" />
    </template>
    <template v-if="$slots.bottom" #bottom="slotProps">
      <slot name="bottom" v-bind="slotProps" />
    </template>
  </GPEditor>
</template>
