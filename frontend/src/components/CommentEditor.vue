<template>
  <TextEditor
    ref="textEditor"
    :editor-class="[
      'prose-sm',
      {
        'min-h-[4rem] overflow-y-auto max-h-[50vh]': editable,
      },
    ]"
    :content="value"
    @change="editable ? $emit('change', $event) : null"
    :starterkit-options="{ heading: { levels: [2, 3, 4, 5, 6] } }"
    placeholder="Add comment..."
    :editable="editable"
  >
    <template v-slot:bottom>
      <div
        v-if="editable"
        class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center"
      >
        <TextEditorFixedMenu
          class="overflow-x-auto"
          :buttons="textEditorMenuButtons"
        />
        <div class="mt-2 flex items-center justify-end space-x-2 sm:mt-0">
          <Button v-bind="discardButtonProps || {}"> Discard </Button>
          <Button appearance="primary" v-bind="submitButtonProps || {}">
            Submit
          </Button>
        </div>
      </div>
    </template>
  </TextEditor>
</template>

<script>
import TextEditor from '@/components/TextEditor.vue'
import { TextEditorFixedMenu } from 'frappe-ui/src/components/TextEditor'

export default {
  name: 'CommentEditor',
  props: [
    'value',
    'editable',
    'editorProps',
    'submitButtonProps',
    'discardButtonProps',
  ],
  emits: ['change'],
  expose: ['editor'],
  components: { TextEditor, TextEditorFixedMenu },
  computed: {
    editor() {
      return this.$refs.textEditor.editor
    },
    textEditorMenuButtons() {
      return [
        'Paragraph',
        ['Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Heading 6'],
        'Separator',
        'Bold',
        'Italic',
        'Separator',
        'Bullet List',
        'Numbered List',
        'Separator',
        'Align Left',
        'Align Center',
        'Align Right',
        'Separator',
        'Image',
        'Link',
        'Blockquote',
        'Code',
        'Horizontal Rule',
        [
          'InsertTable',
          'AddColumnBefore',
          'AddColumnAfter',
          'DeleteColumn',
          'AddRowBefore',
          'AddRowAfter',
          'DeleteRow',
          'MergeCells',
          'SplitCell',
          'ToggleHeaderColumn',
          'ToggleHeaderRow',
          'ToggleHeaderCell',
          'DeleteTable',
        ],
        'Separator',
        'Undo',
        'Redo',
      ]
    },
  },
}
</script>
