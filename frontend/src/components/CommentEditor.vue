<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { Button } from 'frappe-ui'
import { CommentKit, EditorFixedMenu } from 'frappe-ui/editor'
import GPEditor from './editor/GPEditor.vue'
import { gameplanToolbar } from './editor/toolbars'
import { suggestionConfig, richQuoteExtensions } from './editor/config'

// gameplan's comment box: the lighter CommentKit (no table / toc / slash / iframe)
// + @-mentions + #-tags + RichQuote. The shared `gameplanToolbar` self-prunes to
// the comment-available buttons (spec §5), so it needs no separate curation.
const props = withDefaults(
  defineProps<{
    value?: string
    placeholder?: string | null
    editable?: boolean
    submitButtonProps?: Record<string, any>
    discardButtonProps?: Record<string, any>
  }>(),
  { value: '', placeholder: null, editable: true },
)

const emit = defineEmits<{
  change: [value: string]
  'rich-quote': [html: string]
  'rich-quote-click': [payload: { quoteId: string; author: string; content: string }]
}>()

const extensions = computed(() => [
  CommentKit.configure({
    heading: { levels: [2, 3, 4, 5, 6] },
    ...suggestionConfig(true),
  }),
  ...richQuoteExtensions({
    onQuote: (html) => emit('rich-quote', html),
    onQuoteClick: (payload) => emit('rich-quote-click', payload),
  }),
])

const gp = useTemplateRef<InstanceType<typeof GPEditor>>('gp')
const editor = computed(() => gp.value?.editor ?? null)
defineExpose({ editor })
</script>

<template>
  <GPEditor
    ref="gp"
    :extensions="extensions"
    :content="value"
    :placeholder="placeholder ?? undefined"
    :editable="editable"
    :editor-class="['prose-v3 max-w-none', editable && 'min-h-[4rem]']"
    :max-height="editable ? '50vh' : undefined"
    @change="editable ? emit('change', $event) : null"
  >
    <template v-if="editable" #bottom="{ editor: e }">
      <div class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center">
        <EditorFixedMenu :editor="e" :items="gameplanToolbar" class="-ml-1 overflow-x-auto" />
        <div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
          <Button v-bind="discardButtonProps || {}"> Discard </Button>
          <Button variant="solid" v-bind="submitButtonProps || {}"> Submit </Button>
        </div>
      </div>
    </template>
  </GPEditor>
</template>
