<template>
  <GPEditor
    :extensions="extensions"
    :content="modelValue"
    editor-class="prose-v3"
    :placeholder="placeholder"
    :min-height="minHeight"
    :max-height="maxHeight"
    :bubble-menu="gameplanToolbar"
    :floating-menu="gameplanFloatingToolbar"
    autofocus
    @change="(value) => (modelValue = value)"
  />
</template>

<script setup lang="ts">
// A plain rich-text field for `readme`, with no chrome of its own, so whoever
// mounts it decides where saving lives — the About dialog puts Save and Discard
// in the dialog footer. Kept as its own component so tiptap and the gameplan
// toolbars land in the chunk this is async-imported into, not in the caller's.
import GPEditor from '@/components/editor/GPEditor.vue'
import { gameplanFloatingToolbar, gameplanToolbar } from '@/components/editor/toolbars'
import { richTextExtensions } from '@/components/editor/richTextExtensions'

defineOptions({ name: 'ReadmeEditor' })

withDefaults(
  defineProps<{
    placeholder?: string
    minHeight?: string
    maxHeight?: string
  }>(),
  { minHeight: '16rem' },
)

const modelValue = defineModel<string>({ required: true })

const extensions = richTextExtensions()
</script>
